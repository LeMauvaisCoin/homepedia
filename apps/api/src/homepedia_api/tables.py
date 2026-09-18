"""Tables et vues du schéma `public`, pour SQLAlchemy Core.

Fichier généré par `bun run generate` depuis la base locale : ne pas le
modifier à la main. Changer le schéma dans `supabase/migrations`, puis
`bun run supabase:reset` et `bun run generate`.
"""

from geoalchemy2.types import Geometry
from sqlalchemy import CheckConstraint, Column, Index, Integer, MetaData, PrimaryKeyConstraint, Table, Text

metadata = MetaData()


t_territories = Table(
    'territories', metadata,
    Column('code', Text, primary_key=True),
    Column('level', Text, nullable=False),
    Column('name', Text, nullable=False),
    Column('department_code', Text),
    Column('region_code', Text),
    Column('population', Integer),
    Column('centroid', Geometry('POINT', 4326, 2, False, from_text='ST_GeomFromEWKT', name='geometry', nullable=False), nullable=False),
    CheckConstraint("level = ANY (ARRAY['commune'::text, 'departement'::text, 'region'::text])", name='territories_level_check'),
    CheckConstraint('population >= 0', name='territories_population_check'),
    PrimaryKeyConstraint('code', name='territories_pkey'),
    Index('territories_level_name_idx', 'level', 'name'),
    schema='public'
)
