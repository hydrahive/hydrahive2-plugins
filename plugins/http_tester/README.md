# http-tester Plugin

HTTP API Tester für HydraHive2 Agenten.

## Tools

### `request`
Führt HTTP Requests aus (GET/POST/PUT/DELETE).

```yaml
url: "https://api.example.com/users"
method: "GET"
headers:
  Authorization: "Bearer token123"
timeout: 10
```

### `compare`
Vergleicht zwei JSON-Objekte.

```yaml
json1: {"a": 1, "b": 2}
json2: {"a": 1, "c": 3}
ignore_order: false
```

### `validate`
Validiert JSON gegen ein Schema.

```yaml
json: {"name": "Test", "age": 25}
schema:
  type: "object"
  required: ["name"]
  properties:
    name: {type: "string"}
    age: {type: "integer"}
```

## Installation

Im HydraHive2 Frontend:
1. Hub öffnen
2. `http-tester` installieren
3. Agent zuweisen
