-- Cria o banco de dados
CREATE DATABASE catalogo;
USE catalogo;

-- Tabela de usuários (caso use login)
CREATE TABLE Usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    senha VARCHAR(200) NOT NULL
);

-- Tabela de produtos disponíveis no site
CREATE TABLE Produtos (
    id INT AUTO_INCREMENT  PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    imagem VARCHAR(200) NOT NULL
);

-- Tabela de carrinhos (um para cada cliente/sessão)
CREATE TABLE Carrinhos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identificador_cliente VARCHAR(100) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Produtos adicionados ao carrinho
CREATE TABLE Carrinho_Produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    carrinho_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT DEFAULT 1,
    FOREIGN KEY (carrinho_id) REFERENCES Carrinhos(id),
    FOREIGN KEY (produto_id) REFERENCES Produtos(id)
);