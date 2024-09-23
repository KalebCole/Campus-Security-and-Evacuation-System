from flask import Flask, jsonify
from supabase import create_client, Client
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Supabase client
supabase_url = app.config['SUPABASE_URL']
supabase_key = app.config['SUPABASE_API_KEY']
supabase: Client = create_client(supabase_url, supabase_key)

# Simple route to test connection


@app.route('/get-users', methods=['GET'])
def get_users():
    # Query the 'users' table in Supabase
    response = supabase.table('User Entries').select('*').execute()
    print("in get users")
    print(response)
    return jsonify(response.data)


if __name__ == '__main__':
    app.run(debug=True)
