const express = require("express");
const cors = require("cors");
const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");
const WebSocket = require("ws");
const fs = require("fs");
const path = require("path");
const mongoose = require("mongoose");

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 3000;

mongoose.connect("mongodb://localhost:27017/projeto_piec")
    .then(() => console.log("Conectado ao MongoDB com sucesso!"))
    .catch((err) => console.error("Erro ao conectar ao MongoDB:", err));

// Schema e Model para Usuário
const userSchema = new mongoose.Schema({
    name: String,
    matricula: { type: String, unique: true },
    senha: String,
});

const User = mongoose.model("User", userSchema);

// Schema e Model para Registro de Manutenção
const registroManutencaoSchema = new mongoose.Schema({
    maquinaCodigo: String,
    setor: String,
    data: String,
    status: String,
    tecnico: String,
    tipo: String,
    horas: Number,
    pecas: String,
    custo: Number,
    descricao: String,
    observacoes: String
});

const RegistroManutencao = mongoose.model("RegistroManutencao", registroManutencaoSchema);

// Schema e Model para Máquina
const maquinaSchema = new mongoose.Schema({
    nome: String,
    codigo: { type: String, unique: true },
    setor: String,
    fabricante: String,
    serie: String,
    data: String,
    potencia: String,
    estado: String,
    historicoEstados: [{
        estado: String,
        data: String
    }],
    usuarioMatricula: String // Campo para associar a máquina ao usuário
});

const Maquina = mongoose.model("Maquina", maquinaSchema);

// Schema e Model para Agendamento
const agendamentoSchema = new mongoose.Schema({
    maquinaCodigo: String,
    maquinaNome: String,
    data: String,
    descricao: String,
    usuarioMatricula: String // Campo para associar o agendamento ao usuário
});

const Agendamento = mongoose.model("Agendamento", agendamentoSchema);

// Configuração do WebSocket
const wss = new WebSocket.Server({ port: 8080 });

wss.on("connection", (ws) => {
    console.log("Novo cliente conectado ao WebSocket.");

    ws.on("close", () => {
        console.log("Cliente desconectado do WebSocket.");
    });
});

// Função para notificar todos os clientes sobre uma mudança de estado
function notificarMudancaEstado(codigo, estado) {
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ codigo, estado }));
        }
    });
}

// Middleware para verificar o token JWT
function autenticarToken(req, res, next) {
    const authHeader = req.headers["authorization"];
    const token = authHeader && authHeader.split(" ")[1]; // Formato: "Bearer TOKEN"

    if (!token) {
        return res.status(401).json({ error: "Token de autenticação não fornecido." });
    }

    jwt.verify(token, "sua_chave_secreta", (err, user) => {
        if (err) {
            return res.status(403).json({ error: "Token inválido ou expirado." });
        }
        req.user = user; // Adiciona o usuário decodificado à requisição
        next(); // Passa para a próxima função (rota)
    });
}

// Rota para registrar manutenção (protegida)
app.post("/registrar-manutencao", autenticarToken, async (req, res) => {
    const { maquinaCodigo, setor, data, status, tecnico, tipo, horas, pecas, custo, descricao, observacoes } = req.body;

    if (!maquinaCodigo || !data || !status || !tecnico || !tipo || !horas || !custo || !descricao) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    try {
        const novoRegistro = new RegistroManutencao({
            maquinaCodigo,
            setor,
            data,
            status,
            tecnico,
            tipo,
            horas,
            pecas,
            custo,
            descricao,
            observacoes
        });

        await novoRegistro.save();
        res.status(201).json(novoRegistro);
    } catch (error) {
        console.error("Erro ao registrar manutenção:", error);
        res.status(500).json({ error: "Erro ao registrar manutenção." });
    }
});

// Rota para agendar manutenção (protegida)
app.post("/agendar", autenticarToken, async (req, res) => {
    const { maquinaCodigo, data, descricao } = req.body;

    if (!maquinaCodigo || !data || !descricao) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    try {
        const maquina = await Maquina.findOne({ codigo: maquinaCodigo });
        if (!maquina) {
            return res.status(404).json({ error: "Máquina não encontrada." });
        }

        const novoAgendamento = new Agendamento({
            maquinaCodigo,
            maquinaNome: maquina.nome,
            data,
            descricao,
            usuarioMatricula: req.user.matricula // Associar ao usuário logado
        });

        await novoAgendamento.save();
        res.status(201).json(novoAgendamento);
    } catch (error) {
        console.error("Erro ao agendar manutenção:", error);
        res.status(500).json({ error: "Erro ao agendar manutenção." });
    }
});

// Rota para listar usuários (protegida)
app.get("/users", autenticarToken, async (req, res) => {
    try {
        const users = await User.find({}, { senha: 0 }); // Exclui a senha do resultado
        res.json(users);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar usuários." });
    }
});

// Rota para registrar um novo usuário (pública)
app.post("/register", async (req, res) => {
    const { name, matricula, senha } = req.body;

    if (!name || !matricula || !senha) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    try {
        const userExists = await User.findOne({ matricula });
        if (userExists) {
            return res.status(400).json({ error: "Matrícula já cadastrada!" });
        }

        const hashedSenha = await bcrypt.hash(senha, 10);
        const newUser = new User({ name, matricula, senha: hashedSenha });
        await newUser.save();

        res.status(201).json({ message: "Usuário cadastrado com sucesso!" });
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar o usuário." });
    }
});

// Rota para login (pública)
app.post("/login", async (req, res) => {
    const { matricula, senha } = req.body;

    if (!matricula || !senha) {
        return res.status(400).json({ error: "Matrícula e senha são obrigatórios!" });
    }

    try {
        const user = await User.findOne({ matricula });

        if (!user) {
            return res.status(401).json({ error: "Matrícula ou senha incorretos!" });
        }

        const senhaValida = await bcrypt.compare(senha, user.senha);

        if (!senhaValida) {
            return res.status(401).json({ error: "Matrícula ou senha incorretos!" });
        }

        // Gera um token JWT (apenas com a matrícula)
        const token = jwt.sign({ matricula: user.matricula }, "sua_chave_secreta", {
            expiresIn: "1h", // Token expira em 1 hora
        });

        // Retorna o token e o nome do usuário
        res.json({ message: "Login bem-sucedido!", token, user: { name: user.name } });
    } catch (error) {
        console.error("Erro ao fazer login:", error);
        res.status(500).json({ error: "Erro ao fazer login." });
    }
});
// Rota para listar máquinas (protegida)
app.get("/items", autenticarToken, async (req, res) => {
    try {
        const maquinas = await Maquina.find({ usuarioMatricula: req.user.matricula }); // Filtra por usuário
        res.json(maquinas);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar máquinas." });
    }
});

// Rota para listar máquinas (apenas nome e código, protegida)
app.get("/maquinas", autenticarToken, async (req, res) => {
    try {
        const maquinas = await Maquina.find({ usuarioMatricula: req.user.matricula }, { nome: 1, codigo: 1 }); // Filtra por usuário
        res.json(maquinas);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar máquinas." });
    }
});

// Rota para adicionar uma nova máquina (protegida)
app.post("/items", autenticarToken, async (req, res) => {
    const { nome, codigo, setor, fabricante, serie, data, potencia } = req.body;

    if (!nome || !codigo || !setor || !fabricante || !serie || !data || !potencia) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    try {
        const novaMaquina = new Maquina({
            nome,
            codigo,
            setor,
            fabricante,
            serie,
            data,
            potencia,
            estado: "Em operação", // Estado inicial
            historicoEstados: [{ estado: "Em operação", data: new Date().toLocaleString() }], // Histórico inicial
            usuarioMatricula: req.user.matricula // Associar ao usuário logado
        });

        await novaMaquina.save();
        res.status(201).json(novaMaquina);
    } catch (error) {
        if (error.code === 11000) {
            res.status(400).json({ error: "Código da máquina já existe." });
        } else {
            res.status(500).json({ error: "Erro ao salvar a máquina." });
        }
    }
});

// Rota para remover uma máquina (protegida)
app.delete("/items/:id", autenticarToken, async (req, res) => {
    try {
        await Maquina.findByIdAndDelete(req.params.id);
        res.json({ message: "Máquina removida com sucesso." });
    } catch (error) {
        res.status(500).json({ error: "Erro ao remover a máquina." });
    }
});

// Rota para obter o histórico de uma máquina específica (protegida)
app.get("/items/:codigo/historico", autenticarToken, async (req, res) => {
    try {
        const maquina = await Maquina.findOne({ codigo: req.params.codigo, usuarioMatricula: req.user.matricula }); // Filtra por usuário
        if (!maquina) {
            return res.status(404).json({ error: "Máquina não encontrada." });
        }
        res.json(maquina.historicoEstados);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar o histórico." });
    }
});

// Rota para buscar detalhes de uma máquina pelo código (protegida)
app.get("/items/:codigo", autenticarToken, async (req, res) => {
    try {
        const maquina = await Maquina.findOne({ codigo: req.params.codigo, usuarioMatricula: req.user.matricula }); // Filtra por usuário
        if (!maquina) {
            return res.status(404).json({ error: "Máquina não encontrada." });
        }
        res.json(maquina);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar detalhes da máquina." });
    }
});

// Rota para listar agendamentos (protegida)
app.get("/agendamentos", autenticarToken, async (req, res) => {
    try {
        const agendamentos = await Agendamento.find({ usuarioMatricula: req.user.matricula }); // Filtra por usuário
        res.json(agendamentos);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar agendamentos." });
    }
});

// Rota para remover um agendamento (protegida)
app.delete("/agendamentos/:id", autenticarToken, async (req, res) => {
    try {
        await Agendamento.findByIdAndDelete(req.params.id);
        res.json({ message: "Agendamento removido com sucesso." });
    } catch (error) {
        res.status(500).json({ error: "Erro ao remover o agendamento." });
    }
});

// Rota para servir o arquivo TXT (pública)
app.get("/mudancas-estado", (req, res) => {
    const caminhoArquivo = path.join(__dirname, "mudancas_estado.txt"); // Caminho relativo

    if (!fs.existsSync(caminhoArquivo)) {
        return res.status(404).json({ error: "Arquivo de mudanças de estado não encontrado." });
    }

    fs.readFile(caminhoArquivo, "utf-8", (err, data) => {
        if (err) {
            return res.status(500).json({ error: "Erro ao ler o arquivo de mudanças de estado." });
        }
        res.send(data);
    });
});

// Função para ler o arquivo TXT e atualizar o estado das máquinas
async function lerMudancasEstado() {
    const caminhoArquivo = path.join(__dirname, "mudancas_estado.txt"); // Caminho relativo

    if (!fs.existsSync(caminhoArquivo)) {
        console.log("Arquivo de mudanças de estado não encontrado.");
        return;
    }

    try {
        const dados = fs.readFileSync(caminhoArquivo, "utf-8");
        const linhas = dados.split("\n").filter((linha) => linha.trim() !== "");

        // Pega a última linha (última mudança de estado)
        const ultimaLinha = linhas[linhas.length - 1];
        if (ultimaLinha) {
            const estado = ultimaLinha.replace("Estado Previsto: ", "").trim();

            // Atualiza o estado de todas as máquinas
            const maquinas = await Maquina.find();
            for (const maquina of maquinas) {
                if (maquina.estado !== estado) {
                    maquina.estado = estado;
                    maquina.historicoEstados.push({ estado, data: new Date().toLocaleString() });
                    await maquina.save();
                    notificarMudancaEstado(maquina.codigo, estado);
                }
            }

            console.log(`Estado das máquinas atualizado para: ${estado}`);
        }
    } catch (erro) {
        console.error("Erro ao ler o arquivo TXT:", erro);
    }
}

// Ler o arquivo TXT periodicamente (a cada 5 segundos)
setInterval(lerMudancasEstado, 5000);

app.listen(PORT, () => {
    console.log(`Servidor rodando em http://localhost:${PORT}`);
});