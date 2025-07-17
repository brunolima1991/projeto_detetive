from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'segredo_super_secreto'

# --- Listas de Itens do Jogo ---
SUSPEITOS = ["Sargento BIGODE", "Florista DONA BRANCA", "Mordomo JAMES", "Advogado SENHOR MARINHO",
             "Dançarina SRTA ROSA", "Coveiro SÉRGIO SOTURNO", "Chef de Cozinha TONY GOURMET", "Médica DONA VIOLETA"]
ARMAS = ["PÉ DE CABRA", "ESPINGARDA", "FACA", "PÁ", "ARMA QUÍMICA", "SOCO INGLÊS", "VENENO", "TESOURA"]
LOCAIS = ["BANCO", "BOATE", "CEMITÉRIO", "FLORICULTURA", "HOSPITAL", "HOTEL",
          "MANSÃO", "PRAÇA CENTRAL", "PREFEITURA", "RESTAURANTE", "ESTAÇÃO DE TREM"]

def iniciar_estado_jogo():
    """Inicializa ou reseta o estado completo do jogo na sessão do utilizador."""
    # Usa dicionários padrão, que são compatíveis com JSON para a sessão
    session['contadores'] = {'suspeitos': {}, 'armas': {}, 'locais': {}}
    session['revelados'] = {'suspeitos': [], 'armas': [], 'locais': []}
    session.modified = True

@app.route('/')
def index():
    """Renderiza a página inicial."""
    return render_template('index.html')

@app.route('/jogo')
def jogo():
    """Renderiza a página principal do jogo, calculando probabilidades."""
    if 'contadores' not in session or 'revelados' not in session:
        iniciar_estado_jogo()

    contadores = session.get('contadores', {})
    revelados = session.get('revelados', {})
    resultados = {}

    for categoria in ['suspeitos', 'armas', 'locais']:
        base = SUSPEITOS if categoria == 'suspeitos' else ARMAS if categoria == 'armas' else LOCAIS
        
        revelados_categoria = revelados.get(categoria, [])
        contadores_categoria = contadores.get(categoria, {})

        itens_restantes = [item for item in base if item not in revelados_categoria]
        total_palpites_restantes = sum(contadores_categoria.get(item, 0) for item in itens_restantes) or 1
        
        resultados_categoria = []
        for item in base:
            if item in itens_restantes:
                prob = round((contadores_categoria.get(item, 0) / total_palpites_restantes) * 100, 1)
                resultados_categoria.append((item, prob))
            else:
                resultados_categoria.append((item, 0.0))
        resultados[categoria] = resultados_categoria

    def mais_provavel_disponivel(cat):
        """Encontra o item não revelado com o MENOR número de palpites."""
        lista_base = SUSPEITOS if cat == 'suspeitos' else ARMAS if cat == 'armas' else LOCAIS
        revelados_cat = revelados.get(cat, [])
        contadores_cat = contadores.get(cat, {})

        candidatos = [
            (item, contadores_cat.get(item, 0)) for item in lista_base 
            if item not in revelados_cat
        ]
        if not candidatos:
            return None
        return min(candidatos, key=lambda x: x[1])[0]

    sugestao = {
        'suspeito': mais_provavel_disponivel('suspeitos'),
        'arma': mais_provavel_disponivel('armas'),
        'local': mais_provavel_disponivel('locais')
    }

    return render_template(
        'jogo.html',
        suspeitos=SUSPEITOS, 
        armas=ARMAS, 
        locais=LOCAIS,
        resultados=resultados,
        revelados=revelados,
        contadores=contadores,
        sugestao=sugestao
    )

@app.route('/atualizar_estado', methods=['POST'])
def atualizar_estado():
    """Recebe o estado completo do tabuleiro via JSON e atualiza a sessão."""
    data = request.get_json()
    
    new_contadores = {'suspeitos': defaultdict(int), 'armas': defaultdict(int), 'locais': defaultdict(int)}
    new_revelados = {'suspeitos': [], 'armas': [], 'locais': []}

    for categoria, items in data.items():
        if categoria not in new_contadores:
            continue
        for item_name, values in items.items():
            if values.get('revelado'):
                new_revelados[categoria].append(item_name)
            new_contadores[categoria][item_name] = int(values.get('palpites', 0))

    # Converte defaultdict para dict antes de salvar na sessão para evitar problemas de serialização
    session['contadores'] = {k: dict(v) for k, v in new_contadores.items()}
    session['revelados'] = new_revelados
    session.modified = True
    return jsonify({'success': True})

@app.route('/resetar')
def resetar():
    """Limpa os dados da sessão e reinicia o jogo."""
    iniciar_estado_jogo()
    return redirect(url_for('jogo'))

@app.route('/finalizar', methods=['POST'])
def finalizar():
    """Salva o resultado final da partida no histórico."""
    data = request.get_json()
    partida = {
        'suspeito': data.get('suspeito'),
        'arma': data.get('arma'),
        'local': data.get('local'),
        'data': datetime.now().strftime('%d/%m/%Y %H:%M')
    }
    historico = session.get('historico', [])
    historico.insert(0, partida)
    session['historico'] = historico[:10]
    iniciar_estado_jogo()
    return jsonify({'success': True})

@app.route('/historico')
def historico():
    """Exibe a página com o histórico das últimas partidas."""
    return render_template('historico.html', historico=session.get('historico', []))

if __name__ == '__main__':
    app.run(debug=True)

