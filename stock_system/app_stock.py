import pyodbc, bcrypt
from . import db, app

with app.app_context():
    connection = db.engine.raw_connection()  # It establishes connection with db. 
    cursor = connection.cursor()  # Sqlite's cursor.

    def add(newProduct, newProductPrice, newProductQuantity, minimumQuantity):

        # This function adds new products to the stock db.        
        if newProduct in allProduct():
            return f'Error! {newProduct} is already in the stock.'
        try:
            cursor.execute(f"""INSERT INTO Products (name, price, quantity, minimum_quantity) VALUES (?, ?, ?, ?);""",
                        (newProduct, float(newProductPrice), int(newProductQuantity), int(minimumQuantity)))  
            connection.commit()
            return f'{newProduct} has been added.'
        except (ValueError, pyodbc.Error):
            return f'Error! Something went wrong.'

    def update(updateProduct, updateProductPrice=False, updateProductQuantity=False, updatedMinimumQuantity=False):

        # This function updates the products present in the stock db.
        if updateProduct not in allProduct():
            return f'Error! {updateProduct} is not present in the stock.'        
        try:
            info_stock = cursor.execute(f"""Select * From Products Where name = '{updateProduct}';""").fetchall()
            info_stock = [info_stock[0][2], info_stock[0][3], info_stock[0][4]]
            new_price = info_stock[0] if updateProductPrice == '' else updateProductPrice
            new_quantity = info_stock[1] if updateProductQuantity == '' else int(info_stock[1]) + int(updateProductQuantity)
            new_minimum = info_stock[2] if updatedMinimumQuantity == '' else updatedMinimumQuantity

            cursor.execute("""UPDATE Products SET price = ?, quantity = ?, minimum_quantity = ? WHERE name = ?;""",
                        (float(new_price), int(new_quantity), int(new_minimum), updateProduct))        
            connection.commit()
            return f'{updateProduct} has been updated.'
        except (ValueError, pyodbc.Error):
            return f'Error! Something went wrong.'

    def delete(deleteProduct, *args):

        # This function deletes product present in the stock.   
        if deleteProduct not in allProduct():
            return f'Error! {deleteProduct} is not present in the stock.\n'
        else:
            cursor.execute("DELETE FROM Products WHERE name = ?", (deleteProduct,))
            connection.commit() 
            return f'{deleteProduct} has been deleted from stock.'
        
    def read():
        
        # This function reads all the products present in the stock db.
        productsList = cursor.execute('Select * From Products Order By name Asc;').fetchall()
        showProducts = []
        for product in productsList:
            showProducts.append([product[1], float(product[2]), int(product[3]), int(product[4])])
        return showProducts

    def allProduct():
        
        # This function retrieves all the products present in the Products Table.
        products = cursor.execute('Select * From Products').fetchall()
        return [p[1] for p in products]
       
    def register_user(first_name, last_name, password, role):

        # This function creates a new user into the table users.
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute(f"""INSERT INTO Users (first_name, last_name, password, role) VALUES (?, ?, ?, ?);""",
                        (first_name, last_name, hashed_password, role))  
            connection.commit()
            return f'{first_name} has been added.'
        except (ValueError, pyodbc.Error):
            return f'Error! Something went wrong.'

    def check_user(first_name, password, role):

        # This function checks if the information passed by the user matches with the db.
        user_info = cursor.execute("Select * From Users Where first_name = ?", (first_name,)).fetchone()
        if user_info:
            check_password = bcrypt.checkpw(password.encode('utf-8'), user_info[3].encode('utf-8'))  # Checks if passwords match.
            return True if first_name == user_info[1] and check_password and role == user_info[4] else False
        return False