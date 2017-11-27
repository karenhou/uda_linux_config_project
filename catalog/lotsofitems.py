from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import User, Base, Category, EquipmentItem

#engine = create_engine('sqlite:///sportscategory.db')
engine = create_engine('postgresql://catalog:catalog@localhost/catalog')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Rob Stark", email="kingofthenorth@wistro.com")
session.add(User1)
session.commit()

# Create various category and item for testing purpose
cat = Category(user_id=1, name="Soccer")
session.add(cat)
session.commit()

equip = EquipmentItem(
    name="Ball", description="Standard Issue ball", category_id=1)

session.add(equip)
session.commit()

# cat2
cat = Category(user_id=1, name="Football")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="Football",
                      description="Standard Issue football", category_id=2)

session.add(equip)
session.commit()

# cat3
cat = Category(user_id=1, name="Hiking")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="Tents",
                      description="Large tents to sleep", category_id=3)

session.add(equip)
session.commit()

# cat4
cat = Category(user_id=1, name="Skiing")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="gloves",
                      description="Keep you warm", category_id=4)

session.add(equip)
session.commit()

# cat5
cat = Category(user_id=1, name="Baseball")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="Bat",
                      description="standard wooden bat", category_id=5)

session.add(equip)
session.commit()

# cat6
cat = Category(user_id=1, name="Basketball")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="Basketball",
                      description="Standard Issue ball", category_id=6)

session.add(equip)
session.commit()

# cat7
cat = Category(user_id=1, name="Golf")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="Golf Ball",
                      description="Standard Issue golf ball", category_id=7)

session.add(equip)
session.commit()

# cat8
cat = Category(user_id=1, name="Volleyball")

session.add(cat)
session.commit()

equip = EquipmentItem(user_id=1, name="VolleyBall",
                      description="Standard Issue volleyball", category_id=8)

session.add(equip)
session.commit()

print "added lots of Category + Equipment!"
