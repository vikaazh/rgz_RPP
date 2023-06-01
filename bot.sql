CREATE TABLE IF NOT EXISTS stock(
                id serial PRIMARY KEY,
                user_id integer NOT NULL,
                stock_name varchar(10) NOT NULL,
                averages varchar(20)
 )
