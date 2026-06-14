import requests
import json
import time

UIDPASS_FILE = "uidpass.json"
TOKEN_FILE = "tokens.json"
# Nova API fornecida pelo usuário
API_URL = "https://likes-2.vercel.app/token"

def read_uidpass():
    try:
        with open(UIDPASS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo {UIDPASS_FILE} não encontrado.")
        return []

def fetch_token(uid, password):
    url = f"{API_URL}?uid={uid}&password={password}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Conforme o exemplo de resposta, o campo é 'token'
        token = data.get("token")
        if token:
            return token
        else:
            print(f"Aviso: Token não encontrado na resposta para UID {uid}")
            return None
    except Exception as e:
        print(f"Erro ao buscar token para UID {uid}: {e}")
        return None

def update_token_file(token_list):
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {TOKEN_FILE}: {e}")

def main():
    uidpass_list = read_uidpass()
    if not uidpass_list:
        return

    new_tokens = []
    print(f"Iniciando extração de tokens para {len(uidpass_list)} contas...")
    
    for i, item in enumerate(uidpass_list):
        uid = item.get("uid")
        password = item.get("password")
        
        if uid and password:
            print(f"[{i+1}/{len(uidpass_list)}] Buscando token para UID {uid}...")
            token = fetch_token(uid, password)
            if token:
                new_tokens.append({"token": token})
                print(f"Sucesso!")
            
            # Pequeno delay para evitar bloqueios se necessário
            time.sleep(0.5)

    if new_tokens:
        update_token_file(new_tokens)
        print(f"\nConcluído! {len(new_tokens)} tokens salvos em {TOKEN_FILE}.")
    else:
        print("\nNenhum token foi extraído com sucesso.")

if __name__ == "__main__":
    main()
