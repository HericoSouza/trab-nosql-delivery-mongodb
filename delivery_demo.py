import itertools
import json
from datetime import datetime


# ---------- "motor" minimo----------

class ObjectId:
    _counter = itertools.count(1)

    def __init__(self):
        self.value = format(next(ObjectId._counter), '024x')

    def __repr__(self):
        return f"ObjectId('{self.value}')"


def _match(doc, query):
    for key, cond in query.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            for op, target in cond.items():
                if op == "$gte" and not (value is not None and value >= target):
                    return False
                if op == "$lte" and not (value is not None and value <= target):
                    return False
                if op == "$in" and value not in target:
                    return False
        else:
            if value != cond:
                return False
    return True


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count


class Collection:
    def __init__(self, name):
        self.name = name
        self._docs = {}

    def insert_one(self, document):
        doc = dict(document)
        _id = ObjectId()
        doc["_id"] = _id
        self._docs[_id.value] = doc
        return InsertOneResult(_id)

    def find(self, query=None):
        query = query or {}
        return [d for d in self._docs.values() if _match(d, query)]

    def find_one(self, query=None):
        results = self.find(query)
        return results[0] if results else None

    def update_one(self, query, update):
        for doc in self._docs.values():
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$push" in update:
                    for field, value in update["$push"].items():
                        doc.setdefault(field, []).append(value)
                return UpdateResult(1, 1)
        return UpdateResult(0, 0)


class Database:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        return self._collections.setdefault(name, Collection(name))


def to_jsonable(obj):
    if isinstance(obj, ObjectId):
        return repr(obj)
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(v) for v in obj]
    return obj


def pretty(doc_or_list):
    return json.dumps(to_jsonable(doc_or_list), indent=2, ensure_ascii=False)


# ---------- demo ----------

db = Database()

print("=" * 70)
print("1) INSERCAO - restaurante com cardapio aninhado")
print("=" * 70)
cmd1 = '''db.restaurantes.insert_one({
    "nome": "Sabor Caseiro",
    "categoria": "Comida Brasileira",
    "endereco": {"bairro": "Lagoa Nova", "cidade": "Natal"},
    "cardapio": [
        {"item": "Feijoada", "preco": 32.90, "categoria": "Prato principal"},
        {"item": "Coxinha", "preco": 8.50, "categoria": "Salgado"},
        {"item": "Suco de acerola", "preco": 7.00, "categoria": "Bebida"}
    ]
})'''
print(cmd1)
restaurante = {
    "nome": "Sabor Caseiro",
    "categoria": "Comida Brasileira",
    "endereco": {"bairro": "Lagoa Nova", "cidade": "Natal"},
    "cardapio": [
        {"item": "Feijoada", "preco": 32.90, "categoria": "Prato principal"},
        {"item": "Coxinha", "preco": 8.50, "categoria": "Salgado"},
        {"item": "Suco de acerola", "preco": 7.00, "categoria": "Bebida"},
    ],
}
res1 = db.restaurantes.insert_one(restaurante)
print("\n>>> Resultado:")
print(f"InsertOneResult(inserted_id={res1.inserted_id!r})")

print()
print("=" * 70)
print("2) INSERCAO - pedido com itens embutidos (sem tabela separada)")
print("=" * 70)
cmd2 = '''db.pedidos.insert_one({
    "restaurante_id": restaurante_id,
    "cliente": "Joana Lima",
    "itens": [
        {"item": "Feijoada", "quantidade": 1, "preco_unitario": 32.90},
        {"item": "Suco de acerola", "quantidade": 2, "preco_unitario": 7.00}
    ],
    "status": "em preparo",
    "criado_em": datetime.utcnow()
})'''
print(cmd2)
pedido = {
    "restaurante_id": res1.inserted_id,
    "cliente": "Joana Lima",
    "itens": [
        {"item": "Feijoada", "quantidade": 1, "preco_unitario": 32.90},
        {"item": "Suco de acerola", "quantidade": 2, "preco_unitario": 7.00},
    ],
    "status": "em preparo",
    "criado_em": "2026-06-30T18:42:00Z",
}
res2 = db.pedidos.insert_one(pedido)

# segundo pedido para a consulta ter mais de um resultado coerente
db.pedidos.insert_one({
    "restaurante_id": res1.inserted_id,
    "cliente": "Carlos Souza",
    "itens": [{"item": "Coxinha", "quantidade": 4, "preco_unitario": 8.50}],
    "status": "entregue",
    "criado_em": "2026-06-30T17:10:00Z",
})

print("\n>>> Resultado:")
print(f"InsertOneResult(inserted_id={res2.inserted_id!r})")

print()
print("=" * 70)
print('3) CONSULTA - pedidos com status "em preparo"')
print("=" * 70)
cmd3 = 'list(db.pedidos.find({"status": "em preparo"}))'
print(cmd3)
consulta = db.pedidos.find({"status": "em preparo"})
print("\n>>> Resultado:")
print(pretty(consulta))

print()
print("=" * 70)
print("4) ATUALIZACAO - status do pedido (updateOne)")
print("=" * 70)
cmd4 = '''db.pedidos.update_one(
    {"_id": pedido_id},
    {"$set": {"status": "saiu para entrega"}}
)'''
print(cmd4)
upd = db.pedidos.update_one(
    {"_id": res2.inserted_id},
    {"$set": {"status": "saiu para entrega"}},
)
print("\n>>> Resultado:")
print(f"UpdateResult(matched_count={upd.matched_count}, modified_count={upd.modified_count})")

print("\nDocumento apos a atualizacao:")
print(pretty(db.pedidos.find_one({"_id": res2.inserted_id})))
