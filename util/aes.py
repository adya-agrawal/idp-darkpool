from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
import base64

class aes:
    def pad(self, data):
        # Padding for AES (PKCS7)
        pad_len = 16 - (len(data) % 16)
        return data + (chr(pad_len) * pad_len).encode()

    def unpad(self, data):
        # Unpadding for AES
        pad_len = data[-1]
        return data[:-pad_len]

    def generate_aes_key(self):
        # Generates a 256-bit AES key (32 bytes)
        return get_random_bytes(32)

    def encrypt_with_aes(self, aes_key, plaintext):
        cipher = AES.new(aes_key, AES.MODE_CBC)
        iv = cipher.iv
        ciphertext = cipher.encrypt(self.pad(plaintext.encode()))
        # Concatenate the IV and ciphertext, then encode with base64
        return base64.b64encode(iv + ciphertext).decode('utf-8')

    def decrypt_with_aes(self, aes_key, encrypted_text):
        try:
            encrypted_text = base64.b64decode(encrypted_text.encode('utf-8'))
            iv = encrypted_text[:16]  # IV is the first 16 bytes
            ciphertext = encrypted_text[16:]  # The rest is the ciphertext
            cipher = AES.new(aes_key, AES.MODE_CBC, iv)
            decrypted_text = self.unpad(cipher.decrypt(ciphertext))  # Decrypt and unpad
            return decrypted_text.decode('utf-8')  # Return the decoded plaintext
        except (UnicodeDecodeError, ValueError) as e:
            return None  # Return None or simply omit this line to do nothing