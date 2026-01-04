from flask import Flask

from app import create_app

app=create_app()
app.secret_key = 'clave_secreta'

if __name__ == '__main__':
    app.run(debug=True)