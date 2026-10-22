

from flask import Flask, jsonify, render_template, request
import sqlite3
import random
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent

API_KEY = os.getenv("API_KEY")

app = Flask(__name__)


def get_db_connection():
    db_path = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "instance" / "cafes.db")
    )

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/random", methods=["GET"])
def random_choice():
    with get_db_connection() as db:
        row = db.execute(
            "SELECT * FROM cafe ORDER BY RANDOM() LIMIT 1"
        ).fetchone()

        if row is None:
            return jsonify({"error": "No cafes found"}), 404

        return jsonify(dict(row))

@app.route("/all", methods=["GET"])
def all_cafes():
    with get_db_connection() as db:
        rows = db.execute("SELECT * FROM cafe").fetchall()
        return jsonify([dict(row) for row in rows])

@app.route("/search", methods=["GET"])
def search_cafe():
    location = request.args.get("loc", "").strip()

    if not location:
        return jsonify({
            "error": "Please provide a location using ?loc="
        }), 400

    with get_db_connection() as db:
        rows = db.execute(
            "SELECT * FROM cafe WHERE location = ?",
            (location,)
        ).fetchall()

        if not rows:
            return jsonify({
                "error": f"Data not found for {location}"
            }), 404

        return jsonify([dict(row) for row in rows])

@app.route("/add", methods=["POST"])
def add_cafe():
    fields = [
        "name", "map_url", "img_url", "location",
        "has_sockets", "has_toilet", "has_wifi",
        "can_take_calls", "seats", "coffee_price"
    ]

    data = {
        field: request.form.get(field, "").strip()
        for field in fields
    }

    missing = [
        field for field in fields
        if not data[field]
    ]

    if missing:
        return jsonify({
            "error": "Missing fields",
            "fields": missing
        }), 400

    try:
        with get_db_connection() as db:
            db.execute("""
                INSERT INTO cafe (
                    name, map_url, img_url, location,
                    has_sockets, has_toilet, has_wifi,
                    can_take_calls, seats, coffee_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(data[field] for field in fields))

            db.commit()

        return jsonify({
            "message": "Cafe added successfully"
        }), 201

    except sqlite3.Error:
        app.logger.exception("Failed to insert cafe")
        return jsonify({
            "error": "Database operation failed"
        }), 500

@app.route("/update-price/<int:id>", methods=["PATCH"])
def update_price(id):
    price = request.args.get("new_price", "").strip()

    if not price:
        return jsonify({
            "error": "Please provide new_price"
        }), 400

    try:
        with get_db_connection() as db:
            cursor = db.execute(
                "UPDATE cafe SET coffee_price = ? WHERE id = ?",
                (price, id)
            )
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({
                    "error": "Cafe not found"
                }), 404

        return jsonify({
            "message": "Price updated successfully"
        })

    except sqlite3.Error:
        app.logger.exception("Failed to update cafe price")
        return jsonify({
            "error": "Database operation failed"
        }), 500

@app.route("/report-closed/<int:id>",methods=["DELETE"])
def delete(id):
    api_key = request.args.get("api_key")
    if not API_KEY or not api_key or API_KEY != api_key:
        return jsonify({"error": "Invalid API key"}), 401
    with get_db_connection() as db:
        cursor = db.execute("delete from cafe where id=?", (id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Invalid ID"}), 500
        return jsonify({"successful": "cafe data was deleted"})


if __name__ == '__main__':
    app.run()
