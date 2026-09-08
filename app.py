"""Local PortfolioAI application. Run with python app.py."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

load_dotenv(Path(__file__).with_name(".env"))

from src.agents.news import NewsAgent
from src.agents.technical import TechnicalAgent
from src.agents.value import ValueAgent
from src.core.llm import ModelResponseError
from src.data_access.market_data import normalize_ticker


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=16_384, DEMO_MODE=os.getenv("DEMO_MODE", "true").lower() == "true")
    if config:
        app.config.update(config)
    demo = app.config["DEMO_MODE"]
    agents = {"value": ValueAgent(demo), "technical": TechnicalAgent(demo), "news": NewsAgent(demo)}

    @app.get("/")
    def index():
        return render_template("index.html", demo=demo)

    @app.get("/class2")
    def market_page():
        return render_template("class2.html", demo=demo)

    @app.get("/class3")
    def technical_page():
        return render_template("class3.html", demo=demo)

    @app.get("/class4")
    def value_page():
        return render_template("class4.html", demo=demo)

    @app.get("/health")
    def health():
        return jsonify(status="ok", mode="demo" if demo else "live")

    @app.post("/api/<workflow>")
    def analyze(workflow):
        if workflow not in agents:
            return jsonify(error="Unknown workflow."), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Send a JSON object."), 400
        key = "question" if workflow == "news" else "ticker"
        value = data.get(key)
        limit = 1200 if key == "question" else 40
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            return jsonify(error=f"Provide {key} as text between 1 and {limit} characters."), 400
        value = value.strip()
        if key == "ticker":
            try:
                value = normalize_ticker(value)
            except ValueError as exc:
                return jsonify(error=str(exc)), 400
            if demo and value != "DEMO":
                return jsonify(error="Demo mode uses the fictional DEMO ticker. Set DEMO_MODE=false to research real tickers."), 400
        if not demo and not os.getenv("ANTHROPIC_API_KEY", "").strip():
            return jsonify(error="Live mode requires ANTHROPIC_API_KEY. Configure .env or switch to demo mode."), 503
        try:
            result = agents[workflow].run(value)
            return jsonify(**result, mode="demo" if demo else "live")
        except (ValueError, ModelResponseError) as exc:
            return jsonify(error=str(exc)), 422
        except Exception:
            app.logger.exception("Analysis failed for workflow %s", workflow)
            return jsonify(error="An upstream service could not complete the analysis. Try again or switch to demo mode."), 502

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
