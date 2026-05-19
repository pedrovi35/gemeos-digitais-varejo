# MVP Gêmeo Digital · Varejo

Repositório do **Gêmeo Digital de Varejo** — plataforma enterprise de inteligência operacional para supply chain.

## Início rápido

Todo o código da aplicação está em [`project/`](project/).

```bash
cd project
pip install -r requirements.txt
cp .env.example .env
python scripts/bootstrap.py --force
streamlit run app.py
```

Documentação completa: **[project/README.md](project/README.md)**  
Documentação dos modelos (R1–R5, ML, dados, Groq): **[project/docs/](project/docs/)**  
Deploy Streamlit Cloud: **[project/DEPLOY.md](project/DEPLOY.md)**
