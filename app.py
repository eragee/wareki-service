from flask import Flask, request
from datetime import date, datetime
import re
import unicodedata
from helpers import rest_response, rest_error

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False  # preserve field order

# Era start dates (inclusive), newest first
# Reiwa: 2019-05-01, Heisei: 1989-01-08, Showa: 1926-12-25, Taisho: 1912-07-30, Meiji: 1868-01-25
ERAS = [
    ("R", "Reiwa",  "令和",  (2019, 5, 1)),
    ("H", "Heisei", "平成",  (1989, 1, 8)),
    ("S", "Showa",  "昭和",  (1926, 12, 25)),
    ("T", "Taisho", "大正",  (1912, 7, 30)),
    ("M", "Meiji",  "明治",  (1868, 1, 25)),
]
MIN_YEAR = 1868

# Accept codes, romaji, kana, and kanji
ERA_ALIASES = {
    "r": "R", "reiwa": "R", "れいわ": "R", "令和": "R",
    "h": "H", "heisei": "H", "へいせい": "H", "平成": "H",
    "s": "S", "showa": "S", "shouwa": "S", "shōwa": "S", "しょうわ": "S", "昭和": "S",
    "t": "T", "taisho": "T", "taishou": "T", "taishō": "T", "たいしょう": "T", "大正": "T",
    "m": "M", "meiji": "M", "めいじ": "M", "明治": "M",
}

def _normalize_text(s: str) -> str:
    """Trim and NFKC-normalize text (folds full-width digits, etc.)."""
    return unicodedata.normalize("NFKC", s.strip())

def _normalize_era_key(s: str) -> str:
    if s is None:
        return ""
    s = _normalize_text(s)
    low = s.lower()
    # fold common diacritics
    low = (low.replace("ō", "o").replace("ū", "u")
              .replace("â", "a").replace("ê", "e")
              .replace("î", "i").replace("ô", "o").replace("û", "u"))
    return low

def _era_lookup(era_in: str):
    """Find an era by code, romaji, or Japanese name."""
    key = _normalize_era_key(era_in)
    code = ERA_ALIASES.get(key)
    if code:
        return next(e for e in ERAS if e[0] == code)
    for code_, en, ja, (y, m, d) in ERAS:
        if _normalize_era_key(en) == key or _normalize_era_key(ja) == key:
            return (code_, en, ja, (y, m, d))
    return None

def parse_era_year_text(text: str):
    """
    Parse combined era+year inputs like:
      - '令和7年', '平成31年', '昭和64年', '大正1年', '明治45年'
      - '平成元年' (treat 元 as 1)
      - 'Reiwa7', 'Heisei31', 'Showa64' (romaji)
    Returns (era_str, era_year_int) or raises ValueError.
    """
    if not text:
        raise ValueError("Empty input for era_year_text.")
    t = _normalize_text(text)

    # Try Japanese form: <non-digit><(元|digits)><optional 年>
    m = re.match(r"^([^\d0-9]+?)\s*(元|[0-9０-９]+)\s*年?\s*$", t)
    if m:
        era_part = m.group(1)
        year_part = m.group(2)
        if year_part == "元":
            era_year = 1
        else:
            year_part = _normalize_text(year_part)  # fold full-width digits
            era_year = int(year_part)
        return era_part, era_year

    # Try simple romaji form: Reiwa7 / Heisei31 / Showa64
    m2 = re.match(r"^([A-Za-z]+)\s*([0-9０-９]+)\s*$", t)
    if m2:
        era_part = m2.group(1)
        year_part = _normalize_text(m2.group(2))
        era_year = int(year_part)
        return era_part, era_year

    raise ValueError(f"Cannot parse era_year_text: '{text}'")

def from_western_year_only(year: int):
    """Convert by year (boundary year counts as new era)."""
    if year < MIN_YEAR:
        raise ValueError(f"Year must be >= {MIN_YEAR}.")
    for code, en, ja, (sy, sm, sd) in ERAS:
        if year >= sy:
            return {
                "era_en": en,
                "era_ja": ja,
                "era_year": year - sy + 1,
                "year": year,
                "method": "year-only",
                "era_start_date": f"{sy:04d}-{sm:02d}-{sd:02d}"
            }
    raise ValueError("No matching era found.")

def from_western_date(dt: date):
    """Date-accurate conversion (exact boundary days)."""
    if dt.year < MIN_YEAR:
        raise ValueError(f"Year must be >= {MIN_YEAR}.")
    for code, en, ja, (sy, sm, sd) in ERAS:
        if dt >= date(sy, sm, sd):
            return {
                "era_en": en,
                "era_ja": ja,
                "era_year": dt.year - sy + 1,
                "year": dt.year,
                "method": "date",
                "era_start_date": f"{sy:04d}-{sm:02d}-{sd:02d}",
                "date_used": dt.isoformat(),
            }
    raise ValueError("No matching era found.")

def to_western(era_input: str, era_year: int):
    """Convert Japanese era to Western year."""
    if era_year < 1:
        raise ValueError("Era year must be >= 1.")
    era = _era_lookup(era_input)
    if not era:
        raise ValueError(f"Unknown era '{era_input}'.")
    code, en, ja, (sy, sm, sd) = era
    western = sy + era_year - 1
    if western < MIN_YEAR:
        raise ValueError(f"Resulting year is < {MIN_YEAR}.")
    return {
        "era_en": en,
        "era_ja": ja,
        "era_year": era_year,
        "year": western,
        "method": "inverse",
        "era_start_date": f"{sy:04d}-{sm:02d}-{sd:02d}"
    }

def format_output(conv: dict, lang: str):
    """Format final output JSON for response (no AD/西暦, no era_code)."""
    lang = (lang or "en").lower()
    era_label_en = f"{conv['era_en']} {conv['era_year']}"
    era_label_ja = f"{conv['era_ja']}{conv['era_year']}年"
    western_text = str(conv["year"])  # always plain digits

    result = {
        "western_text": western_text,
        "japanese_text": era_label_ja if lang == "ja" else era_label_en,
        "era_en": conv["era_en"],
        "era_ja": conv["era_ja"],
        "era_year": conv["era_year"],
        "year": conv["year"],
    }
    if "date_used" in conv:
        result["date_used"] = conv["date_used"]
    if "era_start_date" in conv:
        result["era_start_date"] = conv["era_start_date"]
    if "method" in conv:
        result["method"] = conv["method"]
    return result

@app.route("/convert", methods=["GET", "POST"])
def convert():
    """
    Inputs (GET or JSON):
      A) Western → Era:
         - year=<int> (>=1868)            [year-only; boundary year => new era]
         - OR date=YYYY-MM-DD             [date-accurate across boundary days]
         - OR now=true                    [use server's current date]
      B) Era → Western:
         - era=<code/romaji/kanji/kana>   (e.g., R, reiwa, 令和, れいわ)
         - era_year=<int >=1>
         - OR era_year_text=<combined>    (e.g., 令和7年, 平成元年, Reiwa7)

      Optional:
         - lang=en|ja (default en)
    """
    try:
        data = request.get_json(silent=True) or (request.args or {})
        lang = data.get("lang", "en")

        # 0) Combined Japanese-style input: '令和7年', '平成元年', 'Reiwa7'
        if data.get("era_year_text"):
            try:
                era_part, era_year = parse_era_year_text(data.get("era_year_text"))
                return rest_response(format_output(to_western(era_part, era_year), lang))
            except ValueError as e:
                return rest_error(str(e))

        # 1) Current date
        if str(data.get("now", "")).lower() in ("true", "1", "yes"):
            dt = date.today()
            return rest_response(format_output(from_western_date(dt), lang))

        # 2) Specific date
        if data.get("date"):
            try:
                dt = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
            except ValueError:
                return rest_error("Invalid 'date'. Use YYYY-MM-DD.")
            return rest_response(format_output(from_western_date(dt), lang))

        # 3) Year or Era-based conversion
        year = data.get("year")
        era = data.get("era")
        era_year = data.get("era_year")

        year = int(year) if (year not in (None, "")) else None
        era_year = int(era_year) if (era_year not in (None, "")) else None

        if year is not None and (era is None and era_year is None):
            conv = from_western_year_only(year)
        elif (era is not None) and (era_year is not None) and (year is None):
            conv = to_western(era, era_year)
        else:
            return rest_error("Provide either year/date/now OR (era and era_year) OR era_year_text, but not both.")

        return rest_response(format_output(conv, lang))

    except ValueError as e:
        return rest_error(str(e))
    except Exception as e:
        return rest_error(f"Internal server error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
