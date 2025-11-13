# wareki-service

A lightweight Flask REST API for converting between Western (Gregorian) years and Japanese era years (和暦 / *wareki*).  
Supports conversions in both directions, including natural Japanese inputs such as “令和7年”.

---

## Features

- Converts from **Western → Japanese era** and **Japanese era → Western**
- Accepts era names in **kanji**, **kana**, or **romaji**
- Parses **combined Japanese-style inputs** like `令和7年` or `平成元年`
- Supports date-based queries (`date=YYYY-MM-DD`) and `now=true`
- Returns clean JSON using `rest_response` / `rest_error`
- UTF-8 output with unsorted JSON keys for stable schema

---

## Example Usage

### Convert Western year → Japanese era

```
GET /convert?year=2025&lang=ja
```

**Response**
```json
{
  "status": "OK",
  "result": {
    "western_text": "2025",
    "japanese_text": "令和7年",
    "era_en": "Reiwa",
    "era_ja": "令和",
    "era_year": 7,
    "year": 2025
  }
}
```

---

### Convert Japanese era → Western year

```
GET /convert?era=昭和&era_year=64
```

**Response**
```json
{
  "status": "OK",
  "result": {
    "western_text": "1989",
    "japanese_text": "Showa 64",
    "era_en": "Showa",
    "era_ja": "昭和",
    "era_year": 64,
    "year": 1989
  }
}
```

---

### Combined Japanese input

```
GET /convert?era_year_text=令和7年
```

**Response**
```json
{
  "status": "OK",
  "result": {
    "western_text": "2025",
    "japanese_text": "令和7年",
    "era_en": "Reiwa",
    "era_ja": "令和",
    "era_year": 7,
    "year": 2025
  }
}
```

---

### Convert a specific date

```
GET /convert?date=2019-04-30
```

**Response**
```json
{
  "status": "OK",
  "result": {
    "western_text": "2019",
    "japanese_text": "Heisei 31",
    "era_en": "Heisei",
    "era_ja": "平成",
    "era_year": 31,
    "year": 2019,
    "date_used": "2019-04-30",
    "era_start_date": "1989-01-08",
    "method": "date"
  }
}
```

---

### Use current date

```
GET /convert?now=true
```

---

## Running Locally

### Requirements

- Python 3.9+
- Flask 3.0+
- psutil (optional, for debugging memory)

### Setup

```bash
git clone https://github.com/<your-username>/wareki-service.git
cd wareki-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Service will run on `http://localhost:5000`.

---

## Deployment (Google Cloud Run)

1. Build image:
   ```bash
   gcloud builds submit --tag gcr.io/<your-project-id>/wareki-service
   ```
2. Deploy:
   ```bash
   gcloud run deploy wareki-service        --image gcr.io/<your-project-id>/wareki-service        --platform managed        --region us-west1        --memory 256Mi        --allow-unauthenticated
   ```

---

## API Summary

| Parameter | Type | Description |
|------------|------|-------------|
| `year` | int | Western year (>= 1868) |
| `date` | string | Western date in YYYY-MM-DD |
| `now` | bool | Use current date |
| `era` | string | Era name (kanji, kana, or romaji) |
| `era_year` | int | Year within the era |
| `era_year_text` | string | Combined input like `令和7年` or `Heisei31` |
| `lang` | string | `en` or `ja` (controls output labels) |

---

## Example JSON Schema

Successful response:
```json
{
  "status": "OK",
  "result": {
    "western_text": "string",
    "japanese_text": "string",
    "era_en": "string",
    "era_ja": "string",
    "era_year": "int",
    "year": "int"
  }
}
```

Error response:
```json
{
  "status": "ERROR",
  "result": "error message"
}
```

## Notes

- Western years prior to 1868 are not supported.
- Boundary year behavior (e.g., 1989) follows official start dates of each era.
- “元年” (*gannen*) is correctly interpreted as year 1.
