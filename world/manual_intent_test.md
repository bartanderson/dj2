1. List all examples (GET)
bash
curl -X GET http://localhost:5000/api/intent/examples
2. Add a new example (POST)

curl -X POST http://localhost:5000/api/intent/examples -H "Content-Type: application/json" -d "{\"intent\": \"acquire_goods\", \"text\": \"i want to obtain a healing potion\", \"is_positive\": true}"

intent: must match an existing intent name (e.g., acquire_goods, dispose_goods, relocate_self, survey_entity, survey_environment, negotiate_price).

text: the example phrase.

is_positive: true for positive examples (should map to this intent), false for negative examples (should not map).

3. Delete an example (DELETE)
First, find the example ID from the GET response, then:

curl -X DELETE http://localhost:5000/api/intent/examples -H "Content-Type: application/json" -d "{\"example_id\": 29}"