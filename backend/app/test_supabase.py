from database import supabase

def test_connection():
    try:
        response = supabase.table("users").select("*").execute()
        print("Conexão bem-sucedida com Supabase!")
        print(response)
    except Exception as e:
        print("Erro ao conectar:", e)

if __name__ == "__main__":
    test_connection()