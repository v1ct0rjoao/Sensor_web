const express = require("express");
const cors = require("cors");
const bcrypt = require("bcrypt");
const WebSocket = require("ws"); // Para suporte a WebSocket
const fs = require("fs"); // Para ler o arquivo TXT
const path = require("path"); // Para manipular caminhos de arquivos

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 3000;

let items = [];
let users = [];

// Configuração do WebSocket
const wss = new WebSocket.Server({ port: 8080 }); // WebSocket na porta 8080

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

// Middleware para verificar o token de autenticação
function authenticateToken(req, res, next) {
    const token = req.headers["authorization"];
    if (!token) return res.status(401).json({ error: "Token de autenticação não fornecido." });

    // Verificar o token (simulado)
    if (token !== "Bearer token_simulado") {
        return res.status(403).json({ error: "Token inválido." });
    }

    next();
}

// Rotas públicas
app.post("/register", async (req, res) => {
    const { name, matricula, senha } = req.body;

    if (!name || !matricula || !senha) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    const userExists = users.find(user => user.matricula === matricula);
    if (userExists) {
        return res.status(400).json({ error: "Matrícula já cadastrada!" });
    }

    const hashedSenha = await bcrypt.hash(senha, 10);
    const newUser = { id: users.length + 1, name, matricula, senha: hashedSenha };
    users.push(newUser);

    res.status(201).json({ message: "Usuário cadastrado com sucesso!" });
});

app.post("/login", async (req, res) => {
    const { matricula, senha } = req.body;

    const user = users.find(user => user.matricula === matricula);
    if (!user) {
        return res.status(401).json({ error: "Matrícula ou senha incorretos!" });
    }

    const senhaValida = await bcrypt.compare(senha, user.senha);
    if (!senhaValida) {
        return res.status(401).json({ error: "Matrícula ou senha incorretos!" });
    }

    res.json({ message: "Login bem-sucedido!", user: { name: user.name } });
});

// Rotas protegidas
app.get("/items", authenticateToken, (req, res) => {
    res.json(items);
});

app.post("/items", authenticateToken, (req, res) => {
    const { nome, codigo, setor, fabricante, serie, data, potencia } = req.body;

    if (!nome || !codigo || !setor || !fabricante || !serie || !data || !potencia) {
        return res.status(400).json({ error: "Todos os campos são obrigatórios!" });
    }

    const newItem = {
        id: items.length + 1,
        nome,
        codigo,
        setor,
        fabricante,
        serie,
        data,
        potencia,
        estado: "Em operação"
    };

    items.push(newItem);
    res.status(201).json(newItem);
});

app.delete("/items/:id", authenticateToken, (req, res) => {
    const { id } = req.params;
    items = items.filter((i) => i.id != id);
    res.json({ message: "Item removido com sucesso" });
});

// Rota para servir o arquivo TXT
app.get("/mudancas-estado", (req, res) => {
    const caminhoArquivo = "C:\\Users\\joaov\\Documents\\Programação\\Projeto_Piec\\Py_sensor\\mudancas_estado.txt";

    // Verifica se o arquivo existe
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
function lerMudancasEstado() {
    const caminhoArquivo = "C:\\Users\\joaov\\Documents\\Programação\\Projeto_Piec\\Py_sensor\\mudancas_estado.txt";

    // Verifica se o arquivo existe
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

            // Atualiza o estado de todas as máquinas (ou de uma máquina específica)
            items.forEach((maquina) => {
                maquina.estado = estado;
                notificarMudancaEstado(maquina.codigo, estado); // Notifica os clientes via WebSocket
            });

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