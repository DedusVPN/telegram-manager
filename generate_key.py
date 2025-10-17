from cryptography.fernet import Fernet

key = Fernet.generate_key().decode()
print("Ваш ENCRYPTION_KEY для .env файла:")
print(key)
