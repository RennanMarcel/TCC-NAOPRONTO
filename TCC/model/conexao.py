import mysql.connector

def iniciaConexao():
    conexaoBanco = mysql.connector.connect(
      host="127.0.0.1",
      user="root",
      password="P@ssAlun0",
      database="CSCJL"
    )
    return conexaoBanco


def createEvento(nome, descricao, dia): 
    conexao = iniciaConexao()
    cursor = conexao.cursor()
    comando = "INSERT INTO evento (nome, descricao, dia) VALUES(%s, %s, %s)"
    valores = [nome, descricao, dia]
    cursor.execute(comando, valores)
    conexao.commit() # edita o banco de dados
    #resultado= cursor.fetchtall() #ler o banco de dados
    print("Evento cadastrado com sucesso")
    cursor.close()
    conexao.close()

def deleteEvento(id):    
    conexao = iniciaConexao()
    cursor = conexao.cursor()
    comando = "DELETE FROM evento WHERE id = %s"
    valores = [id]
    cursor.execute(comando, valores)
    conexao.commit() # edita o banco de dados
    #resultado= cursor.fetchtall() #ler o banco de dados
    print("Evento excluido com sucesso")
    cursor.close()
    conexao.close()


def updateEvento(nome,descricao,dia,id):
     conexao = iniciaConexao()
     cursor = conexao.cursor()
     comando = "UPDATE evento SET nome=%s, dia = %s, descricao = %s WHERE id= %i"
     valores = [nome,descricao,dia,id]
     cursor.execute(comando, valores)
     conexao.commit() # edita o banco de dados
        #resultado= cursor.fetchtall() #ler o banco de dados
     print("Evento atualizado com sucesso")
     cursor.close()
     conexao.close()


def readcardapio():
    conexao = iniciaConexao()
    cursor = conexao.cursor()
    comando = "SELECT * FROM evento;"
    cursor.execute(comando)
    eventos = cursor.fetchall()
    eventos_list = []
    for evento in eventos:
        eventos_list.append({
            'id': evento[0],
            'nome': evento[1],
            'descricao': evento[2],
            'dia': evento[3]
        })
        cursor.close()
        conexao.close()
    return eventos_list

    conexao.commit() # edita o banco de dados
    #resultado= cursor.fetchtall() #ler o banco de dados
    print("Evento")