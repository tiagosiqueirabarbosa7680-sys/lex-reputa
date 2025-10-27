import asyncio
import json
import os
import uuid
from datetime import date
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# ----------------------------------------------------
# 💥 CONFIGURAÇÃO SUPABASE (SUAS CHAVES ESTÃO AQUI) 💥
# ----------------------------------------------------
# URL do Projeto e Chave Pública Inseridas Automaticamente
SUPABASE_URL: str = "https://lagnvipznnxljvxebaeu.supabase.co"
SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZ252aXBwem54bGp2eGViYWV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0ODk4NTEsImV4cCI6MjA3NzA2NTg1MX0.BMkopxQ5kN9xoJiznv2o93pI_dKSi91NYupi1asJDKM"

# Inicializa o cliente Supabase
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(postgrest_client_timeout=10, storage_client_timeout=10)
)
# ----------------------------------------------------

# --- MÓDULOS INTERNOS (PRECISAM SER CRIADOS) ---
# Importa os módulos de lógica de negócio (Scoring e PDF)
# Esses arquivos precisam estar na pasta app/
try:
    from app.compute_score import compute_score
    from app.report import generate_pdf
except ImportError:
    # Se os módulos não existirem, vamos criar uma versão dummy para evitar crash
    print("AVISO: Módulos compute_score ou report não encontrados. Usando funções dummy.")
    def compute_score(processes):
        return {'score_normalized': 72.5, 'details': {}}
    def generate_pdf(entity, processes, score, out_path):
        print(f"DEBUG: PDF gerado (simulação) em {out_path}")
# ----------------------------------------------------


# --- CONFIGURAÇÃO FASTAPI ---
app = FastAPI(
    title="LEX-REPUTA Core API (Supabase Connected)",
    version="1.0.0",
)

# Cria a pasta 'reports' se ela não existir
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


# --- SCHEMAS DE REQUISIÇÃO ---
class SearchRequest(BaseModel):
    """Modelo para a requisição de busca."""
    query: str
    cpf_cnpj: str = None
    tribunals: List[str] = ["TJSP", "TJMG"] # Exemplo de default


# --- SIMULAÇÃO DE SCRAPER ---
def simulate_scraper(query: str) -> List[Dict[str, Any]]:
    """Simula a execução do scraper e retorna dados brutos."""
    today = date.today().strftime("%Y-%m-%d")
    
    # Processos simulados para o scoring
    return [
        {
            "tribunal": "TJSP",
            "process_number": f"0001-{uuid.uuid4().hex[:4]}",
            "process_type": "execucao",
            "status": "ativo",
            "last_movement_date": today,
            "summary": "Processo de execução fiscal em andamento."
        },
        {
            "tribunal": "TJMG",
            "process_number": f"0002-{uuid.uuid4().hex[:4]}",
            "process_type": "trabalhista",
            "status": "arquivado",
            "last_movement_date": (date.today().replace(year=date.today().year - 5)).strftime("%Y-%m-%d"),
            "summary": "Reclamação trabalhista antiga, já arquivada."
        },
        {
            "tribunal": "TRF3",
            "process_number": f"0003-{uuid.uuid4().hex[:4]}",
            "process_type": "improbidade",
            "status": "julgado_procedente",
            "last_movement_date": (date.today().replace(month=1)).strftime("%Y-%m-%d"),
            "summary": "Ação civil pública por improbidade administrativa."
        }
    ]


# --- ROTAS DA API ---

@app.get("/")
async def root():
    """Verificação simples de saúde do servidor."""
    return {"status": "ok", "message": "API rodando e conectada ao Supabase."}


@app.post("/search")
async def search(req: SearchRequest):
    """Inicia a busca reputacional, calcula o score e armazena os dados."""
    
    # 1. SIMULAR SCRAPING
    process_list = simulate_scraper(req.query)

    # 2. CALCULAR SCORE
    score_data = compute_score(process_list)
    
    # 3. SALVAR ENTIDADE NO BANCO
    try:
        entity_data = {
            "name": req.query,
            "cpf_cnpj": req.cpf_cnpj,
            "entity_type": "pj" if req.cpf_cnpj and len(req.cpf_cnpj) > 14 else "pf"
        }
        
        # Insere e retorna o ID da entidade
        # Nota: O uso de .execute() é síncrono, ok para o MVP
        entity_res = supabase.table("entities").insert(entity_data).execute()
        
        if not entity_res.data:
             raise Exception("Inserção de entidade falhou.")

        entity_id = entity_res.data[0]['id']
        
    except Exception as e:
        # Erro comum é a falta das tabelas no Supabase
        raise HTTPException(status_code=400, detail=f"Erro ao inserir entidade. Verifique se as tabelas existem no Supabase. Erro: {e}")

    # 4. SALVAR PROCESSOS NO BANCO
    processes_to_insert = [
        {**p, "entity_id": entity_id} for p in process_list
    ]
    
    # Inserção em massa
    supabase.table("processes").insert(processes_to_insert).execute()
    
    # 5. GERAR PDF E ARMAZENAR CAMINHO
    report_filename = f"{entity_id}.pdf"
    report_path_local = os.path.join(REPORTS_DIR, report_filename)
    
    generate_pdf(
        entity={"name": req.query}, 
        processes=process_list, 
        score=score_data['score_normalized'], 
        out_path=report_path_local
    )
    
    # 6. SALVAR SCORE FINAL NO BANCO
    reputation_data = {
        "entity_id": entity_id,
        "score": score_data['score_normalized'],
        "risk_level": "Alto" if score_data['score_normalized'] < 50 else "Baixo",
        "details": score_data,
        "report_path": f"/reports/{report_filename}",
        "score_method_version": "v1.0"
    }
    supabase.table("reputations").insert(reputation_data).execute()
    
    # 7. RETORNO PARA O FRONTEND
    return {
        "status": "concluido",
        "entity_id": entity_id,
        "score": score_data['score_normalized'],
        "risk_level": reputation_data['risk_level'],
        "total_processes": len(process_list),
        "download_url": f"http://127.0.0.1:8000/report/{entity_id}.pdf"
    }

# Rota para download do relatório
@app.get("/report/{entity_id}.pdf")
async def get_report(entity_id: str):
    """Retorna o PDF gerado (para teste local)."""
    report_path_local = os.path.join(REPORTS_DIR, f"{entity_id}.pdf")
    
    if not os.path.exists(report_path_local):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    from fastapi.responses import FileResponse
    return FileResponse(report_path_local, media_type="application/pdf", filename=f"Relatorio_{entity_id}.pdf")