"""Régénère `homepedia_api/tables.py` depuis la base locale migrée (ADR-0002)."""

import sys
from pathlib import Path

import geoalchemy2  # noqa: F401  # enregistre les types PostGIS pour l'introspection
from sqlacodegen.generators import TablesGenerator
from sqlalchemy import MetaData, create_engine, make_url

from homepedia_api.settings import get_settings

HEADER = '''"""Tables et vues du schéma `public`, pour SQLAlchemy Core.

Fichier généré par `bun run generate` depuis la base locale : ne pas le
modifier à la main. Changer le schéma dans `supabase/migrations`, puis
`bun run supabase:reset` et `bun run generate`.
"""

'''


def main() -> None:
    target = Path(sys.argv[1])
    url = make_url(str(get_settings().database_url)).set(drivername="postgresql+psycopg")
    engine = create_engine(url)
    metadata = MetaData()
    with engine.connect() as connection:
        metadata.reflect(connection, schema="public", views=True)
        code = TablesGenerator(metadata, connection, options=()).generate()
    engine.dispose()
    target.write_text(HEADER + code)


if __name__ == "__main__":
    main()
