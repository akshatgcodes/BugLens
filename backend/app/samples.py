"""Small, deliberately buggy programs to try BugLens on. Shown in the UI's sample menu."""

SAMPLES = [
    {
        "id": "flask-api",
        "title": "Flask API (Python)",
        "language": "python",
        "filename": "app.py",
        "code": """import sqlite3

import yaml
from flask import Flask, request

app = Flask(__name__)
DB_PASSWORD = "hunter2-prod"


def get_db():
    return sqlite3.connect("app.db")


@app.route("/user")
def get_user():
    user_id = request.args.get("id")
    db = get_db()
    row = db.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()
    if row == None:
        return {"error": "not found"}, 404
    return {"id": row[0], "name": row[1]}


@app.route("/settings", methods=["POST"])
def save_settings():
    settings = yaml.load(request.data)
    return {"saved": len(settings)}


def average(values=[]):
    total = 0
    for v in values:
        total += v
    return total / len(values)


def parse_amount(text):
    try:
        return eval(text)
    except:
        return 0


if __name__ == "__main__":
    app.run(debug=True)
""",
    },
    {
        "id": "express-api",
        "title": "Express handler (JavaScript)",
        "language": "javascript",
        "filename": "server.js",
        "code": """const express = require("express");
const { exec } = require("child_process");
const db = require("./db");

const app = express();
const apiKey = "live_8f3k2j5h7g9d1s4a";

app.get("/search", async (req, res) => {
  const q = req.query.q;
  const rows = await db.query(`SELECT * FROM products WHERE name LIKE '%${q}%'`);
  console.log("search", q, rows.length);
  res.send("<h1>Results for " + q + "</h1>" + rows.map((r) => r.name).join("<br>"));
});

app.post("/thumbnail", (req, res) => {
  exec("convert " + req.body.file + " -resize 200x200 thumb.png", (err) => {
    if (err) res.status(500).end();
    res.send("ok");
  });
});

function applyDiscount(price, code) {
  var discount = 0;
  if (code == "SAVE10") discount = 0.1;
  try {
    discount += JSON.parse(code).extra;
  } catch (e) {}
  return price - price * discount;
}

app.listen(3000);
""",
    },
    {
        "id": "ts-cart",
        "title": "Shopping cart (TypeScript)",
        "language": "typescript",
        "filename": "cart.ts",
        "code": """interface Item {
  id: string;
  price: number;
  qty: number;
}

export class Cart {
  private items: Item[] = [];

  add(item: Item) {
    const existing = this.items.find((i) => i.id == item.id);
    if (existing) existing.qty + item.qty;
    else this.items.push(item);
  }

  remove(id: string) {
    this.items.splice(this.items.findIndex((i) => i.id === id), 1);
  }

  total(): number {
    return this.items.reduce((sum, i) => sum + i.price * i.qty, 0);
  }

  // TODO: persist the cart
  load(raw: string) {
    const data: any = JSON.parse(raw);
    this.items = data.items;
  }
}

export function sessionToken(): string {
  return Math.random().toString(36).slice(2);
}
""",
    },
    {
        "id": "java-login",
        "title": "Login check (Java)",
        "language": "java",
        "filename": "LoginService.java",
        "code": """import java.security.MessageDigest;
import java.sql.*;

public class LoginService {
    private static final String DB_PASSWORD = "Pr0d-Passw0rd!";
    private Connection conn;

    public boolean login(String user, String password) throws Exception {
        Statement st = conn.createStatement();
        ResultSet rs = st.executeQuery(
            "SELECT hash FROM users WHERE name = '" + user + "'");
        if (!rs.next()) return false;
        MessageDigest md = MessageDigest.getInstance("MD5");
        String hash = new String(md.digest(password.getBytes()));
        return hash == rs.getString("hash");
    }

    public String role(String user) {
        try {
            if (user == "admin") return "admin";
            return lookupRole(user);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private String lookupRole(String user) { return "user"; }
}
""",
    },
    {
        "id": "go-handler",
        "title": "HTTP handler (Go)",
        "language": "go",
        "filename": "main.go",
        "code": """package main

import (
	"crypto/tls"
	"database/sql"
	"fmt"
	"net/http"
	"os/exec"
)

var db *sql.DB

func userHandler(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	row := db.QueryRow(fmt.Sprintf("SELECT name FROM users WHERE id = %s", id))
	var name string
	row.Scan(&name)
	fmt.Fprintf(w, "Hello %s", name)
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	host := r.URL.Query().Get("host")
	out, _ := exec.Command("sh", "-c", "ping -c 1 "+host).Output()
	w.Write(out)
}

func fetch(url string) (*http.Response, error) {
	client := &http.Client{Transport: &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}}
	return client.Get(url)
}

func main() {
	http.HandleFunc("/user", userHandler)
	http.HandleFunc("/ping", pingHandler)
	_ = http.ListenAndServe(":8080", nil)
}
""",
    },
]
