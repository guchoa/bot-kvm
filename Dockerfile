# Imagem base com Python 3.11 slim (leve e rápido)
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo requirements.txt para instalar dependências
COPY requirements.txt .

# Instala as dependências do seu bot
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo do seu projeto para dentro do container
COPY . .

# Expõe a porta usada pelo keep_alive (Flask)
EXPOSE 8080

# Comando para rodar seu bot
CMD ["python", "bot.py"]
