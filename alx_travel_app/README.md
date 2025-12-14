# alx_travel_app_0x01

API for managing listings and bookings using Django REST framework, with Swagger documentation.

## Endpoints

- `GET /api/listings/`: List all listings
- `POST /api/listings/`: Create a listing
- `GET /api/listings/{id}/`: Retrieve a listing
- `PUT /api/listings/{id}/`: Update a listing
- `PATCH /api/listings/{id}/`: Partial update
- `DELETE /api/listings/{id}/`: Delete a listing

- `GET /api/bookings/`: List all bookings
- `POST /api/bookings/`: Create a booking
- `GET /api/bookings/{id}/`: Retrieve a booking
- `PUT /api/bookings/{id}/`: Update a booking
- `PATCH /api/bookings/{id}/`: Partial update
- `DELETE /api/bookings/{id}/`: Delete a booking

## Swagger Docs

- Swagger UI: `http://localhost:8000/swagger/`
- OpenAPI JSON/YAML: `http://localhost:8000/swagger.json` or `http://localhost:8000/swagger.yaml`

## Quick Start (Windows PowerShell)

```powershell
# Create and apply migrations
python .\alx_travel_app\manage.py makemigrations listings
python .\alx_travel_app\manage.py migrate

# Run server
python .\alx_travel_app\manage.py runserver
```

## Testing with Postman

- Import the Swagger URL `http://localhost:8000/swagger.json` in Postman to generate requests.
- Verify CRUD for `/api/listings/` and `/api/bookings/`.

## Notes

- Ensure `rest_framework` and `drf_yasg` are installed. If missing, add to `requirement.txt` and install.
