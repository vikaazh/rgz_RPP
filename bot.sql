CREATE TABLE IF NOT EXISTS stocks(
                id serial PRIMARY KEY,
                user_id integer NOT NULL,
                stock_name varchar(10) NOT NULL,
                averages varchar(20),
				         ticker varchar(20)
)
