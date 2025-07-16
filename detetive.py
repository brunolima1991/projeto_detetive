from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'segredo_super_secreto'

SUSPEITOS = ["Sargento BIGODE", "Florista DONA BRANCA", "Mordomo JAMES", "Advogado SENHOR MARINHO",
             "Dançarina SRTA ROSA", "Coveiro SÉRGIO SOTURNO", "Chef de Cozinha TONY GOURMET", "Médica DONA VIOLETA"]
ARMAS = ["PÉ DE CABRA", "ESPINGARDA", "FACA", "PÁ", "ARMA QUÍMICA", "SOCO INGLÊS", "VENENO", "TESOURA"]
LOCAIS = ["BANCO", "BOATE", "CEMITÉRIO", "FLORICULTURA", "HOSPITAL", "HOTEL",
          "MANSÃO", "PRAÇA CENTRAL", "PREFEITURA", "RESTAURANTE", "ESTAÇÃO DE TREM"]

def iniciar_contadores():
    return {'suspeitos': defaultdict(int), 'armas': defaultdict(int), 'locais': defaultdict(int)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jogo')
def jogo():
    if 'contadores' not in session:
        session['contadores'] = iniciar_contadores()

    contadores = session['contadores']
    resultados, saiu = {}, {}

    for categoria in ['suspeitos', 'armas', 'locais']:
        base = SUSPEITOS if categoria == 'suspeitos' else ARMAS if categoria == 'armas' else LOCAIS
        saiu[categoria] = [item for item, count in contadores[categoria].items() if count > 0]
        # Itens não revelados
        itens_restantes = [item for item in base if item not in saiu[categoria]]
        # Total só dos itens não revelados
        total = sum(contadores[categoria].get(item, 0) for item in itens_restantes) or 1
        resultados[categoria] = [
            (item, round((contadores[categoria].get(item, 0) / total) * 100, 1)) if item in itens_restantes else (item, 0.0)
            for item in base
        ]

    # Lógica da "Hipótese Sugerida" 🕵️
    def mais_provavel_disponivel(cat, lista):
        candidatos = [(item, contadores[cat].get(item, 0)) for item in lista if item not in saiu[cat]]
        if not candidatos:
            return None
        return min(candidatos, key=lambda x: x[1])[0]  # o que foi menos citado (ainda viável)

    sugestao = {
        'suspeito': mais_provavel_disponivel('suspeitos', SUSPEITOS),
        'arma': mais_provavel_disponivel('armas', ARMAS),
        'local': mais_provavel_disponivel('locais', LOCAIS)
    }

    return render_template(
        'jogo.html',
        suspeitos=SUSPEITOS,
        armas=ARMAS,
        locais=LOCAIS,
        resultados=resultados,
        saiu=saiu,
        sugestao=sugestao,
        contadores=contadores  # Garante que contadores é passado ao template
    )


@app.route('/registrar_palpite', methods=['POST'])
def registrar_palpite():
    data = request.get_json()
    categoria, item = data.get('categoria'), data.get('item')

    if 'contadores' not in session:
        session['contadores'] = iniciar_contadores()

    session['contadores'][categoria][item] += 1
    contadores = session['contadores']
    resultados, saiu = {}, {}

    for categoria in ['suspeitos', 'armas', 'locais']:
        total = sum(contadores.get(categoria, {}).values()) or 1
        base = SUSPEITOS if categoria == 'suspeitos' else ARMAS if categoria == 'armas' else LOCAIS
        resultados[categoria] = [(item, round((contadores[categoria].get(item, 0) / total) * 100, 1)) for item in base]
        saiu[categoria] = [item for item, count in contadores[categoria].items() if count > 0]

    return jsonify({'resultados': resultados, 'saiu': saiu})

@app.route('/resetar')
def resetar():
    session['contadores'] = iniciar_contadores()
    return redirect(url_for('jogo'))

@app.route('/finalizar', methods=['GET', 'POST'])
def finalizar():
    if request.method == 'POST':
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
        session['contadores'] = iniciar_contadores()
        return jsonify({'success': True})
    else:
        return render_template('finalizar.html')

@app.route('/historico')
def historico():
    return render_template('historico.html', historico=session.get('historico', []))

@app.route('/limpar_historico')
def limpar_historico():
    session['historico'] = []
    return redirect(url_for('jogo'))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
