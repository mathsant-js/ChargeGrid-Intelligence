from __future__ import annotations

from pathlib import Path

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, KeepTogether, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "chargegrid_sprint_3.pdf"
ARCH = ROOT / "docs" / "sprint-3" / "diagrams" / "architecture.png"
SEQ = ROOT / "docs" / "sprint-3" / "diagrams" / "sequence.png"
DASHBOARD_TOP = ROOT / "docs" / "sprint-3" / "screenshots" / "captura_dashboard_gestor_kpis_graficos.png"
DASHBOARD_BOTTOM = ROOT / "docs" / "sprint-3" / "screenshots" / "captura_dashboard_gestor_operacao_alertas.png"

NAVY = HexColor("#071C2C")
NAVY2 = HexColor("#0D2B3E")
GREEN = HexColor("#35D39A")
MINT = HexColor("#B9F5DE")
CYAN = HexColor("#4CC9F0")
ORANGE = HexColor("#FFB45B")
RED = HexColor("#FF6B6B")
INK = HexColor("#132A36")
MUTED = HexColor("#58717E")
PAPER = HexColor("#F5F8F7")
LINE = HexColor("#D6E2E0")
WHITE = colors.white


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, doc.pagesize[0], 1.15 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MINT)
    canvas.drawString(1.5 * cm, 0.43 * cm, "CHARGEGRID INTELLIGENCE | SPRINT 3 | PROTÓTIPO SIMULADO")
    canvas.drawRightString(doc.pagesize[0] - 1.5 * cm, 0.43 * cm, f"{doc.page}")
    canvas.restoreState()


class AccentBox(Flowable):
    def __init__(self, text, color=GREEN, width=17.5 * cm):
        super().__init__(); self.text=text; self.color=color; self.width=width; self.height=1.35*cm
    def draw(self):
        self.canv.setFillColor(HexColor("#EAF5F1")); self.canv.roundRect(0,0,self.width,self.height,7,fill=1,stroke=0)
        self.canv.setFillColor(self.color); self.canv.rect(0,0,0.14*cm,self.height,fill=1,stroke=0)
        self.canv.setFillColor(INK); self.canv.setFont("Helvetica-Bold",9)
        self.canv.drawString(.42*cm,.51*cm,self.text)


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=GREEN, spaceAfter=7, tracking=1.4))
    s.add(ParagraphStyle(name="H1x", fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=NAVY, spaceAfter=12))
    s.add(ParagraphStyle(name="H2x", fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY, spaceBefore=4, spaceAfter=9))
    s.add(ParagraphStyle(name="H3x", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK, spaceBefore=6, spaceAfter=4))
    s.add(ParagraphStyle(name="Bodyx", fontName="Helvetica", fontSize=9, leading=13.2, textColor=INK, spaceAfter=7))
    s.add(ParagraphStyle(name="Smallx", fontName="Helvetica", fontSize=7.5, leading=10.5, textColor=MUTED, spaceAfter=5))
    s.add(ParagraphStyle(name="Callout", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8))
    s.add(ParagraphStyle(name="Cover", fontName="Helvetica-Bold", fontSize=31, leading=34, textColor=WHITE, spaceAfter=12))
    s.add(ParagraphStyle(name="CoverSub", fontName="Helvetica", fontSize=13, leading=18, textColor=MINT, spaceAfter=8))
    s.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=7.7, leading=10, textColor=INK))
    s.add(ParagraphStyle(name="CellHead", fontName="Helvetica-Bold", fontSize=7.7, leading=9, textColor=WHITE))
    return s


S = styles()


def table(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands=[("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),.35,LINE),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]
    if header:
        commands += [("BACKGROUND",(0,0),(-1,0),NAVY2),("TEXTCOLOR",(0,0),(-1,0),WHITE)]
    for r in range(1 if header else 0, len(data)):
        if r % 2 == 0: commands.append(("BACKGROUND",(0,r),(-1,r),HexColor("#EEF4F2")))
    t.setStyle(TableStyle(commands)); return t


def p(text, style="Bodyx"): return Paragraph(text, S[style])
def cell(text, head=False): return Paragraph(text, S["CellHead" if head else "Cell"])


def energy_chart():
    d=Drawing(500,210)
    d.add(Rect(0,0,500,210,rx=10,ry=10,fillColor=WHITE,strokeColor=LINE))
    c=VerticalBarChart(); c.x=55; c.y=42; c.height=125; c.width=390
    c.data=[[60,60,60],[0,0,20]]; c.categoryAxis.categoryNames=["11:58 | 3 sessões","11:59 | 4 sessões","12:00 | 4 sessões"]
    c.valueAxis.valueMin=0; c.valueAxis.valueMax=90; c.valueAxis.valueStep=20
    c.bars[0].fillColor=CYAN; c.bars[1].fillColor=GREEN; c.bars.strokeColor=None
    c.categoryAxis.labels.fontSize=7; c.valueAxis.labels.fontSize=7
    d.add(c); d.add(String(18,184,"Potência por fonte em cada tick (kW)",fontName="Helvetica-Bold",fontSize=11,fillColor=NAVY))
    leg=Legend(); leg.x=330; leg.y=190; leg.fontSize=7; leg.colorNamePairs=[(CYAN,"Rede"),(GREEN,"Solar")]; d.add(leg)
    return d


def dashboard_visual():
    d=Drawing(500,260)
    d.add(Rect(0,0,500,260,rx=12,ry=12,fillColor=NAVY,strokeColor=None))
    d.add(String(18,235,"VISUALIZAÇÃO DO ENSAIO SIMULADO",fontName="Helvetica-Bold",fontSize=8,fillColor=GREEN))
    d.add(String(18,214,"Operação energética integrada",fontName="Helvetica-Bold",fontSize=17,fillColor=WHITE))
    cards=[(18,"80 kW","potência total",GREEN),(136,"60 kW","rede (limite)",CYAN),(254,"20 kW","solar",ORANGE),(372,"HIGH","alerta",RED)]
    for x,val,label,col in cards:
        d.add(Rect(x,150,105,48,rx=7,ry=7,fillColor=NAVY2,strokeColor=HexColor("#24495A")))
        d.add(String(x+9,177,val,fontName="Helvetica-Bold",fontSize=14,fillColor=col)); d.add(String(x+9,160,label,fontName="Helvetica",fontSize=7,fillColor=MINT))
    d.add(Rect(18,35,459,94,rx=7,ry=7,fillColor=HexColor("#0A2233"),strokeColor=HexColor("#24495A")))
    vals=[20,15,20]; labels=["Tick 1\n3 × 20 kW","Tick 2\n4 × 15 kW","Tick 3\n4 × 20 kW"]
    for i,v in enumerate(vals):
        x=55+i*140; h=v*3.2
        d.add(Rect(x,55,42,h,fillColor=GREEN,strokeColor=None)); d.add(String(x+8,59+h,f"{v} kW",fontName="Helvetica-Bold",fontSize=8,fillColor=WHITE))
        d.add(String(x-3,43,labels[i].replace("\n"," | "),fontName="Helvetica",fontSize=6.5,fillColor=MINT))
    return d


def cover(canvas, doc):
    canvas.saveState(); w,h=doc.pagesize
    canvas.setFillColor(NAVY); canvas.rect(0,0,w,h,fill=1,stroke=0)
    canvas.setFillColor(GREEN); canvas.circle(w-2.5*cm,h-2.7*cm,4.2*cm,fill=1,stroke=0)
    canvas.setFillColor(NAVY2); canvas.circle(w-2.5*cm,h-2.7*cm,3.35*cm,fill=1,stroke=0)
    canvas.setStrokeColor(GREEN); canvas.setLineWidth(5)
    canvas.line(1.55*cm,6.0*cm,w-1.55*cm,6.0*cm)
    canvas.setFont("Helvetica-Bold",8); canvas.setFillColor(GREEN); canvas.drawString(1.55*cm,h-2.0*cm,"FIAP × GOODWE | EQUIPE 3 | SPRINT 3")
    canvas.setFont("Helvetica-Bold",31); canvas.setFillColor(WHITE); canvas.drawString(1.55*cm,h-7.0*cm,"ChargeGrid")
    canvas.drawString(1.55*cm,h-8.25*cm,"Intelligence")
    canvas.setFont("Helvetica",12); canvas.setFillColor(MINT); canvas.drawString(1.55*cm,h-9.3*cm,"Integração, automação e eficiência para recarga elétrica")
    canvas.setFont("Helvetica-Bold",10); canvas.setFillColor(WHITE); canvas.drawString(1.55*cm,4.85*cm,"RELATÓRIO TÉCNICO DO PROTÓTIPO SIMULADO")
    canvas.setFont("Helvetica",8); canvas.setFillColor(MINT); canvas.drawString(1.55*cm,4.25*cm,"Pensamento Computacional e Automação com Python")
    canvas.drawString(1.55*cm,3.75*cm,"21 de setembro de 2026")
    canvas.restoreState()


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc=BaseDocTemplate(str(OUT),pagesize=A4,rightMargin=1.55*cm,leftMargin=1.55*cm,topMargin=1.35*cm,bottomMargin=1.55*cm,title="ChargeGrid Intelligence - Sprint 3",author="Equipe 3")
    portrait=Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="portrait")
    land=Frame(1.35*cm,1.45*cm,landscape(A4)[0]-2.7*cm,landscape(A4)[1]-2.7*cm,id="land")
    doc.addPageTemplates([PageTemplate(id="cover",pagesize=A4,onPage=cover,frames=[portrait]),PageTemplate(id="portrait",pagesize=A4,onPage=footer,frames=[portrait]),PageTemplate(id="landscape",pagesize=landscape(A4),onPage=footer,frames=[land])])
    story=[Spacer(1,23*cm),NextPageTemplate("portrait"),PageBreak()]
    story += [p("VISÃO EXECUTIVA","Kicker"),p("Uma plataforma que transforma recarga em decisão energética","H1x"),p("O <b>ChargeGrid Intelligence</b> integra sessões de recarga, gestão de demanda, prioridade solar, dados, cobrança e indicadores ambientais em um monólito modular demonstrável. Nesta Sprint 3, a integração é comprovada por um cenário automatizado e reproduzível, com componentes físicos substituídos por provedores simulados explicitamente identificados.")]
    story += [AccentBox("DEMONSTRAÇÃO INTEGRADA: sessão → alocação → solar/rede → leitura → alerta → billing → ESG"),Spacer(1,.35*cm)]
    story += [table([[cell("Entregável",True),cell("Evidência no protótipo",True)],[cell("Integração"),cell("React → API FastAPI → serviços → SQLAlchemy/PostgreSQL")],[cell("Automação"),cell("Seed idempotente, roteiro HTTP e ticks manuais determinísticos")],[cell("Eficiência"),cell("Limite de 60 kW da rede e rateio Equal Share")],[cell("Sustentabilidade"),cell("Prioridade solar e cálculo de CO₂ evitado")],[cell("Qualidade"),cell("179 testes backend, 14 frontend, lint, tipos e build aprovados no ensaio registrado")]], [4.2*cm,13.3*cm])]
    story += [Spacer(1,.3*cm),p("Escopo e transparência","H2x"),p("As grandezas apresentadas são <b>simuladas</b>. Não houve medição em carregador, inversor ou medidor físico. Não há OCPP/Modbus, agendador de ticks ou modelo de ML treinado nesta entrega; o risco de pico preditivo permanece para fase posterior. Essa delimitação preserva a rastreabilidade técnica do MVP."),PageBreak()]
    story += [p("EQUIPE E CONTEXTO","Kicker"),p("Equipe 3 - FIAP × GoodWe","H1x")]
    members=[("Bernardo Zauza Amorim","568808"),("Bruno Almeida de Oliveira","572648"),("Gabriel Góes Nunes Pereira","571735"),("Guilherme Vinciguerra Carvalho","571951"),("Marcos Peterson Martins Pereira","573857"),("Matheus Jorge Santana","574166")]
    rows=[[cell("Nome completo",True),cell("RM",True)]]+[[cell(name),cell(rm)] for name,rm in members]
    story += [table(rows,[13.5*cm,4*cm]),Spacer(1,.4*cm),p("Problema abordado","H2x"),p("Quando quatro veículos solicitam 20 kW cada, a demanda chega a 80 kW, acima dos 60 kW disponíveis da rede. O sistema precisa limitar a importação, dividir potência de forma previsível, aproveitar solar antes da rede e registrar consequências operacionais, financeiras e ambientais."),PageBreak()]
    story += [p("ARQUITETURA EXECUTADA","Kicker"),p("Integração dos componentes","H1x"),p("O navegador React consome contratos REST sob <b>/api/v1</b>. A API FastAPI coordena serviços de sessão, simulação, energia, billing e analytics. O SQLAlchemy persiste os dados em PostgreSQL. O provedor solar é intercambiável e, nesta sprint, entrega uma curva determinística simulada."),Image(str(ARCH),width=17.4*cm,height=3.73*cm),Spacer(1,.25*cm)]
    story += [table([[cell("Componente",True),cell("Responsabilidade",True),cell("Contribuição",True)],[cell("React + TypeScript"),cell("Dashboards e interação"),cell("Visibilidade operacional e atualização manual")],[cell("FastAPI + Pydantic"),cell("Contratos e orquestração"),cell("Automação rastreável com validação")],[cell("Serviços de domínio"),cell("Sessões, alocação, billing e ESG"),cell("Regras centralizadas e testáveis")],[cell("Simulador"),cell("Relógio, curva solar e ticks"),cell("Ensaio seguro sem hardware")],[cell("PostgreSQL + SQLAlchemy"),cell("Persistência e consultas"),cell("Histórico para auditoria e análise")]], [4.0*cm,6.1*cm,7.3*cm]),Spacer(1,.25*cm),AccentBox("ML é consultivo: previsões futuras nunca poderão violar os limites determinísticos de energia."),NextPageTemplate("landscape"),PageBreak()]
    story += [KeepTogether([p("FLUXO PONTA A PONTA","Kicker"),p("Sequência funcional da demonstração","H1x"),Image(str(SEQ),width=22.6*cm,height=14.51*cm),p("Cada seta corresponde a uma rota, serviço ou persistência existente. O tick é manual; o script apenas encadeia chamadas públicas.","Smallx")]),NextPageTemplate("portrait"),PageBreak()]
    story += [p("APLICAÇÃO EM EXECUÇÃO","Kicker"),p("Dashboard administrativo: energia e sustentabilidade","H1x"),Image(str(DASHBOARD_TOP),width=17.2*cm,height=18.42*cm),Spacer(1,.15*cm),p("Figura 3. Captura real do dashboard do gestor após a execução do cenário simulado da Sprint 3. A interface consolida demanda, limite da rede, utilização solar, sessões, faturamento e indicadores ambientais.","Smallx"),p("Após o encerramento da quarta sessão, três recargas permanecem ativas: a demanda total é 60 kW, atendida por 15 kW solares e 45 kW da rede. Os gráficos preservam o histórico do cenário anterior, no qual a entrega chegou a 80 kW com quatro sessões."),PageBreak()]
    story += [p("EVIDÊNCIA OPERACIONAL","Kicker"),p("Sessões, histórico e alertas","H1x"),Image(str(DASHBOARD_BOTTOM),width=16.5*cm,height=18.56*cm),Spacer(1,.15*cm),p("Figura 4. Recorte da mesma captura real, com sessões, faturamento, leituras persistidas e alertas operacionais.","Smallx"),p("O histórico registra a evolução de 20 kW por sessão para o rateio de 15 kW e, depois, a contribuição solar de 5 kW por sessão. O alerta <b>High grid demand</b> confirma que a importação atingiu o limite configurado de 60 kW."),PageBreak()]
    story += [p("RESULTADOS FUNCIONAIS","Kicker"),p("Medições reproduzidas pelo roteiro","H1x"),energy_chart(),Spacer(1,.15*cm)]
    data=[[cell(x,True) for x in ["Tick UTC","Sessões","Alocação","Solar","Rede","Energia"]],[cell("11:58"),cell("3"),cell("3 × 20 = 60 kW"),cell("0 kW"),cell("60 kW"),cell("1,0000 kWh")],[cell("11:59"),cell("4"),cell("4 × 15 = 60 kW"),cell("0 kW"),cell("60 kW"),cell("1,0000 kWh")],[cell("12:00"),cell("4"),cell("4 × 20 = 80 kW"),cell("20 kW"),cell("60 kW"),cell("1,3333 kWh")]]
    story += [table(data,[2*cm,1.7*cm,4.3*cm,2.2*cm,2.2*cm,3.1*cm]),Spacer(1,.3*cm),table([[cell("Indicador",True),cell("Resultado",True),cell("Interpretação",True)],[cell("Alerta"),cell("HIGH_DEMAND"),cell("Demanda elevada registrada para decisão do gestor")],[cell("Invoice"),cell("CLOSED - R$ 0,47"),cell("Billing pay-per-use com tarifa de R$ 0,8000/kWh")],[cell("CO₂ evitado"),cell("0,1333 kg"),cell("Solar utilizada × fator de 0,4 kg/kWh")],[cell("Validação"),cell("179 + 14 testes"),cell("Backend e frontend, além de lint, tipos e build")]], [3.2*cm,4.2*cm,10.1*cm]),PageBreak()]
    story += [p("JUSTIFICATIVAS TÉCNICAS","Kicker"),p("Escolhas orientadas a correção e demonstração","H1x")]
    choices=[("Monólito modular","Reduz infraestrutura e mantém fronteiras claras entre API, domínio, simulação, billing e analytics."),("Equal Share","É determinístico, simples de explicar e distribui o recurso escasso igualmente, respeitando limites individuais."),("Solar priorizada","Reduz importação da rede e torna explícito o aproveitamento renovável em cada leitura."),("Ticks manuais","Permitem repetir o cenário minuto a minuto e inspecionar o efeito de cada decisão."),("PostgreSQL + migrations","Garantem persistência estruturada, histórico e evolução de esquema reproduzível."),("UTC + Decimal","UTC evita ambiguidade temporal; tipos decimais preservam valores monetários."),("API tipada","Pydantic e TypeScript reduzem inconsistências entre backend e frontend."),("Simulação desacoplada","EnergyDataProvider permite substituir a fonte simulada por integração física futura sem mover regras críticas.")]
    rows=[[cell("Escolha",True),cell("Justificativa",True)]]+[[cell(a),cell(b)] for a,b in choices]
    story += [table(rows,[4.4*cm,13.1*cm]),Spacer(1,.25*cm),AccentBox("Invariante central: potência alocada nunca é negativa nem excede pedido, carregador, veículo ou limite da rede."),PageBreak()]
    story += [p("SUSTENTABILIDADE E AUTOMAÇÃO","Kicker"),p("Como cada tecnologia gera valor","H1x")]
    story += [table([[cell("Dimensão",True),cell("Mecanismo",True),cell("Efeito demonstrado",True)],[cell("Sustentabilidade"),cell("Prioridade solar + segregação solar/rede + fator de emissão"),cell("20 kW solares no terceiro tick e 0,1333 kg de CO₂ evitado na API")],[cell("Automação inteligente"),cell("Seed, script HTTP, controlador, alertas e regras determinísticas"),cell("Cenário inteiro repetível sem intervenção no banco durante o fluxo")],[cell("Eficiência energética"),cell("Limite de rede e rateio Equal Share"),cell("Quatro sessões atendidas sem exceder 60 kW de importação")],[cell("Eficiência operacional"),cell("Dashboards, histórico e billing integrados"),cell("Estado energético convertido em alerta, invoice e indicadores")]], [3.6*cm,6.8*cm,7.1*cm]),Spacer(1,.35*cm),p("Cadeia de valor","H2x"),p("<b>Recarga → dados → informação → inteligência → decisão energética.</b> A plataforma não se limita a registrar consumo: ela relaciona restrição elétrica, fonte energética, evento operacional, custo e impacto ambiental. Essa integração é o núcleo da proposta de valor."),p("Limites e evolução responsável","H2x"),p("O protótipo não comanda potência física. A futura conexão com equipamentos deve entrar pela fronteira do provedor de dados/integração, mantendo os serviços determinísticos como autoridade sobre segurança energética. Um modelo preditivo poderá estimar demanda e classificar risco, mas terá caráter consultivo."),PageBreak()]
    story += [p("CONEXÃO COM A DISCIPLINA","Kicker"),p("Pensamento Computacional e Automação com Python","H1x")]
    story += [table([[cell("Conteúdo",True),cell("Aplicação no ChargeGrid",True)],[cell("Decomposição"),cell("Separação em sessões, energia, simulação, billing, analytics e persistência")],[cell("Abstração"),cell("Modelos de usuário, veículo, carregador, estação, leitura e invoice")],[cell("Algoritmos"),cell("Cálculo de potência solicitada, Equal Share, prioridade solar, energia, custo e ESG")],[cell("Automação em Python"),cell("FastAPI, controlador de ticks, seed idempotente e roteiro de demonstração")],[cell("Estruturas e persistência"),cell("Schemas Pydantic, entidades SQLAlchemy e PostgreSQL")],[cell("Testes e validação"),cell("Invariantes energéticas, transições, APIs e fluxo integrado automatizados")],[cell("Dados e tomada de decisão"),cell("Dashboards, alerta HIGH_DEMAND, histórico, cobrança e sustentabilidade")]], [4.5*cm,13*cm]),Spacer(1,.35*cm),p("Síntese acadêmica","H2x"),p("O projeto materializa o pensamento computacional ao decompor um problema físico e multidimensional em dados, regras e interfaces verificáveis. A automação em Python coordena o experimento, enquanto os testes convertem requisitos energéticos em critérios objetivos. Assim, o software demonstra sustentabilidade e eficiência sem depender de uma alegação de hardware inexistente."),PageBreak()]
    story += [p("REPRODUÇÃO E RASTREABILIDADE","Kicker"),p("Como verificar a demonstração","H1x"),p("1. Configurar ambiente de demonstração isolado, relógio UTC opt-in e fator de emissão de 0,4 kg/kWh.<br/>2. Subir os serviços via Docker Compose e aplicar migrations.<br/>3. Executar o seed idempotente com senhas fornecidas apenas por variáveis de ambiente.<br/>4. Rodar <b>scripts/sprint3_demo.py</b>, que usa endpoints públicos.<br/>5. Conferir OpenAPI, dashboards, leituras, alerta, invoice e sustentabilidade.<br/>6. Executar <b>make check</b> para validar backend e frontend."),AccentBox("As credenciais permanecem fora do Git; a demonstração deve usar banco limpo e um único controlador de simulação."),Spacer(1,.35*cm),p("Fontes internas consultadas","H2x"),p("SPEC.md (fonte de verdade técnica e regras); BRIEFING.md (visão, disciplina e organização); docs/SPRINT_3_PLAN.md; docs/sprint-3/README.md; docs/sprint-3/EVIDENCE.md; diagramas Mermaid/PNG; código e testes do backend/frontend.","Bodyx"),p("Conclusão","H2x"),p("A Sprint 3 apresenta um protótipo simulado integrado, rastreável e demonstrável. O sistema mantém a rede em seu limite, redistribui potência, incorpora energia solar, persiste leituras, emite alerta, encerra sessão, calcula cobrança e apresenta indicador ambiental. O resultado conecta automação inteligente, sustentabilidade e eficiência energética em um único fluxo coerente."),Spacer(1,.4*cm),p("CHARGEGRID INTELLIGENCE","Callout"),p("Transformando cada recarga em inteligência acionável.","Callout")]
    doc.build(story)
    print(OUT)


if __name__ == "__main__": build()
