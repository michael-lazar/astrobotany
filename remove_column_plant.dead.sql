CREATE TABLE IF NOT EXISTS "new_plant" ("id" INTEGER NOT NULL PRIMARY KEY, "user_id" INTEGER NOT NULL, "user_active_id" INTEGER, "created_at" DATETIME NOT NULL, "updated_at" DATETIME NOT NULL, "w
atered_at" DATETIME NOT NULL, "watered_by_id" INTEGER, "generation" INTEGER NOT NULL, "score" INTEGER NOT NULL, "stage" INTEGER NOT NULL, "species" INTEGER NOT NULL, "rarity" INTEGER NOT NULL, "color" INTEGER NOT NULL, "mutation" INTEGER,"name" TEXT NOT NULL, "fertilized_at" DATETIME NOT NULL, "shaken_at" INTEGER NOT NULL, FOREIGN KEY ("user_id") REFERENCES "user" ("id"), FOREIGN KEY ("user_active_id") REFERENCES "user" ("id"), FOREIGN KEY ("watered_by_id") REFERENCES "user" ("id"));
INSERT INTO new_plant select id, user_id, user_active_id, created_at, updated_at, watered_at, watered_by_id, generation, score, stage, species, rarity, color, mutation, name, fertilized_at, shaken_at from plant;
DROP TABLE plant;
ALTER TABLE new_plant RENAME TO plant;
CREATE INDEX "plant_user_id" ON "plant" ("user_id");
CREATE UNIQUE INDEX "plant_user_active_id" ON "plant" ("user_active_id");
CREATE INDEX "plant_watered_by_id" ON "plant" ("watered_by_id");

