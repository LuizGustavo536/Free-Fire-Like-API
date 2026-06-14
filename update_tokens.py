import requests
import json
import time
import sys

UIDPASS_FILE = "uidpass.json"
TOKEN_FILE = "tokens.json"
# Nova API fornecida pelo usuário
API_URL = "https://likes-2.vercel.app/token"

def read_uidpass():
    try:
        with open(UIDPASS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo {UIDPASS_FILE} não encontrado.", flush=True)
        return []

def fetch_token(uid, password):
    url = f"{API_URL}?uid={uid}&password={password}"
    try:
        # Timeout curto para não travar o workflow se a API estiver lenta
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        token = data.get("token")
        if token:
            return token
        else:
            # Se não tiver token, pode ser conta banida ou erro na API
            return None
    except Exception as e:
        # Silencioso para não poluir o log se houver muitos erros de timeout/ban
        return None

def update_token_file(token_list):
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_list, f, ensure_ascii=False, indent=4)
        print(f"Arquivo {TOKEN_FILE} atualizado com sucesso.", flush=True)
    except Exception as e:
        print(f"Erro ao salvar {TOKEN_FILE}: {e}", flush=True)

def main():
    uidpass_list = read_uidpass()
    if not uidpass_list:
        print("Nenhuma conta encontrada em uidpass.json.", flush=True)
        return

    new_tokens = []
    total = len(uidpass_list)
    print(f"Iniciando extração de tokens para {total} contas...", flush=True)
    
    start_time = time.time()
    
    for i, item in enumerate(uidpass_list):
        uid = item.get("uid")
        password = item.get("password")
        
        if uid and password:
            # Log de progresso a cada 5 contas para não inundar o log do GitHub
            if (i + 1) % 5 == 0 or (i + 1) == total:
                print(f"Processando: {i+1}/{total}...", flush=True)
            
            token = fetch_token(uid, password)
            if token:
                new_tokens.append({"token": token})
            
            # Pequeno delay para respeitar a API
            time.sleep(0.1)

    print(f"\nProcessamento concluído em {int(time.time() - start_time)} segundos.", flush=True)
    
    if new_tokens:
        update_token_file(new_tokens)
        print(f"Total de tokens extraídos: {len(new_tokens)}", flush=True)
    else:
        print("Nenhum token válido foi extraído. Verifique as contas ou a API.", flush=True)

if __name__ == "__main__":
    main()
