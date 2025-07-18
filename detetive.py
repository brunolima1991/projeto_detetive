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
TODAS_AS_CARTAS = sorted(SUSPEITOS + ARMAS + LOCAIS)

def iniciar_estado_jogo():
    """Inicializa ou reseta o estado completo do jogo na sessão do utilizador."""
    session['contadores'] = {'suspeitos': {}, 'armas': {}, 'locais': {}}
    session['revelados'] = {'suspeitos': [], 'armas': [], 'locais': []}
    session['nome_jogador'] = 'Detetive'
    session.modified = True

def calcular_sugestao(contadores, revelados):
    """Calcula a sugestão de acusação com base na carta não revelada com mais palpites."""
    def mais_provavel_disponivel(cat):
        lista_base = SUSPEITOS if cat == 'suspeitos' else ARMAS if cat == 'armas' else LOCAIS
        revelados_cat = revelados.get(cat, [])
        contadores_cat = contadores.get(cat, {})
        candidatos = [
            (item, contadores_cat.get(item, 0)) for item in lista_base 
            if item not in revelados_cat
        ]
        if not candidatos: return None
        return max(candidatos, key=lambda x: x[1])[0]

    return {
        'suspeito': mais_provavel_disponivel('suspeitos'),
        'arma': mais_provavel_disponivel('armas'),
        'local': mais_provavel_disponivel('locais')
    }

def calcular_probabilidades(contadores, revelados):
    """Calcula a porcentagem de chance de cada item com base nos palpites."""
    probabilidades = {}
    for categoria in ['suspeitos', 'armas', 'locais']:
        base = SUSPEITOS if categoria == 'suspeitos' else ARMAS if categoria == 'armas' else LOCAIS
        revelados_categoria = revelados.get(categoria, [])
        contadores_categoria = contadores.get(categoria, {})
        
        itens_restantes = [item for item in base if item not in revelados_categoria]
        total_palpites_restantes = sum(contadores_categoria.get(item, 0) for item in itens_restantes) or 1
        
        lista_prob = []
        for item in base:
            if item in itens_restantes:
                prob = round((contadores_categoria.get(item, 0) / total_palpites_restantes) * 100, 1)
                lista_prob.append({'nome': item, 'prob': prob})
            else:
                lista_prob.append({'nome': item, 'prob': 0.0})
        probabilidades[categoria] = lista_prob
    return probabilidades

@app.route('/')
def index():
    """Renderiza a página inicial."""
    return render_template('index.html', todas_as_cartas=TODAS_AS_CARTAS)

@app.route('/iniciar_nova_partida', methods=['POST'])
def iniciar_nova_partida():
    """Processa o formulário de setup."""
    iniciar_estado_jogo()
    nome_jogador = request.form.get('nome_jogador', 'Detetive')
    cartas_recebidas = request.form.getlist('cartas[]')
    session['nome_jogador'] = nome_jogador
    revelados = session.get('revelados')
    for carta in cartas_recebidas:
        if carta in SUSPEITOS: revelados['suspeitos'].append(carta)
        elif carta in ARMAS: revelados['armas'].append(carta)
        elif carta in LOCAIS: revelados['locais'].append(carta)
    session['revelados'] = revelados
    session.modified = True
    return redirect(url_for('jogo'))

@app.route('/jogo')
def jogo():
    """Renderiza a página principal do jogo."""
    if 'contadores' not in session:
        return redirect(url_for('index'))

    contadores = session.get('contadores', {})
    revelados = session.get('revelados', {})
    nome_jogador = session.get('nome_jogador', 'Detetive')
    
    sugestao_inicial = {'suspeito': '...', 'arma': '...', 'local': '...'}
    probabilidades = calcular_probabilidades(contadores, revelados)

    return render_template(
        'jogo.html',
        nome_jogador=nome_jogador,
        suspeitos=SUSPEITOS, armas=ARMAS, locais=LOCAIS,
        revelados=revelados,
        contadores=contadores,
        sugestao=sugestao_inicial,
        probabilidades=probabilidades
    )

@app.route('/atualizar_estado', methods=['POST'])
def atualizar_estado():
    """Recebe o estado do tabuleiro, atualiza a sessão e retorna a nova sugestão e probabilidades."""
    data = request.get_json()
    
    new_contadores = session.get('contadores', {'suspeitos': {}, 'armas': {}, 'locais': {}})
    new_revelados = session.get('revelados', {'suspeitos': [], 'armas': [], 'locais': []})

    for categoria, items in data.items():
        if categoria not in new_contadores: continue
        for item_name, values in items.items():
            is_revelado = values.get('revelado', False)
            if is_revelado and item_name not in new_revelados[categoria]:
                new_revelados[categoria].append(item_name)
            elif not is_revelado and item_name in new_revelados[categoria]:
                new_revelados[categoria].remove(item_name)
            new_contadores[categoria][item_name] = int(values.get('palpites', 0))

    session['contadores'] = new_contadores
    session['revelados'] = new_revelados
    session.modified = True

    nova_sugestao = calcular_sugestao(new_contadores, new_revelados)
    novas_probabilidades = calcular_probabilidades(new_contadores, new_revelados)
    
    return jsonify({'success': True, 'sugestao': nova_sugestao, 'probabilidades': novas_probabilidades})

# O resto do ficheiro (resetar, finalizar, historico) permanece igual
@app.route('/resetar')
def resetar():
    iniciar_estado_jogo()
    return redirect(url_for('index'))

@app.route('/finalizar', methods=['POST'])
def finalizar():
    data = request.get_json()
    partida = {
        'nome_jogador': session.get('nome_jogador', 'Anónimo'),
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
    return render_template('historico.html', historico=session.get('historico', []))

if __name__ == '__main__':
    app.run(debug=True)

