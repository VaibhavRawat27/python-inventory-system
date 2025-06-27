import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from datetime import datetime, timedelta
import uuid
import webbrowser

# ==============================================
# Data Management Functions
# ==============================================
def load_inventory():
    try:
        return pd.read_csv("data/inventory.csv")
    except:
        return pd.DataFrame(columns=["product_id", "name", "quantity", "price", "min_stock"])

def save_inventory(df):
    df.to_csv("data/inventory.csv", index=False)

def load_transactions():
    try:
        return pd.read_csv("data/transactions.csv")
    except:
        return pd.DataFrame(columns=["date", "time", "product_id", "quantity_sold"])

def save_transactions(df):
    df.to_csv("data/transactions.csv", index=False)

def load_bills():
    try:
        return pd.read_csv("data/bills.csv")
    except:
        return pd.DataFrame(columns=["bill_id", "date", "product", "quantity", "price", "subtotal", "tax", "total", "customer"])

def save_bills(df):
    df.to_csv("data/bills.csv", index=False)

# ==============================================
# Utility Functions
# ==============================================
def refresh_inventory_table(filter_txt=""):
    for item in inventory_tree.get_children():
        inventory_tree.delete(item)
    inv = load_inventory()
    if filter_txt:
        inv = inv[inv["name"].str.contains(filter_txt, case=False)]
    for _, row in inv.iterrows():
        inventory_tree.insert("", "end", values=(row["product_id"], row["name"], row["quantity"], f"₹{row['price']:.2f}"))

def show_low_stock_badge():
    inv = load_inventory()
    low = inv[inv["quantity"] < inv["min_stock"]]
    if not low.empty:
        low_stock_btn.config(text=f"⚠️ Low Stock ({len(low)})", style="Warning.TButton")
    else:
        low_stock_btn.config(text="Inventory Healthy", style="Safe.TButton")

# ==============================================
# Window Classes
# ==============================================
class LowStockDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Low Stock Alert")
        self.top.geometry("500x400")
        
        inv = load_inventory()
        low_stock = inv[inv["quantity"] < inv["min_stock"]]
        
        if low_stock.empty:
            label = ttk.Label(self.top, text="All products have sufficient stock.", padding=10)
            label.pack()
        else:
            frame = ttk.Frame(self.top)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            tree = ttk.Treeview(frame, columns=("ID", "Name", "Current", "Minimum", "Needed"), 
                               show="headings")
            
            tree.heading("ID", text="ID")
            tree.heading("Name", text="Product Name")
            tree.heading("Current", text="Current Qty")
            tree.heading("Minimum", text="Min Qty")
            tree.heading("Needed", text="Needed")
            
            tree.column("ID", width=50, anchor="center")
            tree.column("Name", width=150)
            tree.column("Current", width=80, anchor="center")
            tree.column("Minimum", width=80, anchor="center")
            tree.column("Needed", width=80, anchor="center")
            
            for _, row in low_stock.iterrows():
                needed = row["min_stock"] - row["quantity"]
                tree.insert("", "end", values=(
                    row["product_id"],
                    row["name"],
                    row["quantity"],
                    row["min_stock"],
                    needed
                ))
            
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            ttk.Button(self.top, text="Generate Purchase Order", 
                      command=lambda: generate_purchase_order(low_stock)).pack(pady=10)
        
        ttk.Button(self.top, text="Close", command=self.top.destroy).pack(pady=10)

class BillingWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Generate New Bill")
        self.top.geometry("400x600")  # Make the window smaller
        self.top.resizable(False, False)
        
        # Configure styles
        self.top.configure(bg="#f5f5f5")
        style = ttk.Style()
        style.configure("Billing.TFrame", background="#f5f5f5")
        style.configure("Billing.TLabel", background="#f5f5f5", font=("Arial", 10))
        style.configure("Billing.TButton", font=("Arial", 10), padding=5)
        
        self.current_items = []
        
        # Header
        header_frame = ttk.Frame(self.top, style="Billing.TFrame")
        header_frame.pack(pady=10, padx=10, fill="x")
        ttk.Label(header_frame, text="NEW BILL", style="Billing.TLabel", 
                 font=("Arial", 14, "bold")).pack(side="left")
        
        # Customer Info
        customer_frame = ttk.Frame(self.top, style="Billing.TFrame")
        customer_frame.pack(pady=5, padx=10, fill="x")
        
        ttk.Label(customer_frame, text="Customer Name:", style="Billing.TLabel").grid(row=0, column=0, sticky="w")
        self.customer_entry = ttk.Entry(customer_frame)
        self.customer_entry.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Product Add Section
        add_frame = ttk.Frame(self.top, style="Billing.TFrame")
        add_frame.pack(pady=10, padx=10, fill="x")
        
        ttk.Label(add_frame, text="Product ID:", style="Billing.TLabel").grid(row=0, column=0)
        self.product_id_entry = ttk.Entry(add_frame)
        self.product_id_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Quantity:", style="Billing.TLabel").grid(row=0, column=2)
        self.quantity_entry = ttk.Entry(add_frame)
        self.quantity_entry.grid(row=0, column=3, padx=5)
        
        add_btn = ttk.Button(add_frame, text="Add Item", command=self.add_item, style="Billing.TButton")
        add_btn.grid(row=1, column=0, padx=5)
        
        # Items Table
        self.tree_frame = ttk.Frame(self.top, style="Billing.TFrame")
        self.tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        columns = ("Product", "Quantity", "Price", "Subtotal")
        self.bill_tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.bill_tree.heading(col, text=col)
            self.bill_tree.column(col, anchor="center", width=120)
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.bill_tree.yview)
        self.bill_tree.configure(yscrollcommand=scrollbar.set)
        
        self.bill_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Summary Section
        summary_frame = ttk.Frame(self.top, style="Billing.TFrame")
        summary_frame.pack(pady=5, padx=10, fill="x")
        
        self.summary_label = ttk.Label(summary_frame, text="Subtotal: ₹0.00 | Tax: ₹0.00 | Total: ₹0.00", 
                                      style="Billing.TLabel", font=("Arial", 10, "bold"))
        self.summary_label.pack(anchor="e")
        
        # Buttons
        btn_frame = ttk.Frame(self.top, style="Billing.TFrame")
        btn_frame.pack(pady=10, fill="x")
        
        ttk.Button(btn_frame, text="Generate Bill", command=self.confirm_generate_bill, 
                  style="Billing.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all, 
                  style="Billing.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.top.destroy, 
                  style="Billing.TButton").pack(side="right", padx=5)
    
    def add_item(self):
        try:
            pid = int(self.product_id_entry.get())
            qty = int(self.quantity_entry.get())
            inv = load_inventory()
            
            if pid not in inv["product_id"].values:
                messagebox.showerror("Error", "Product not found.")
                return
            
            product = inv[inv["product_id"] == pid].iloc[0]
            
            if product["quantity"] < qty:
                messagebox.showerror("Error", f"Only {product['quantity']} units available.")
                return
            
            subtotal = qty * product["price"]
            
            self.current_items.append({
                "product_id": pid,
                "name": product["name"],
                "quantity": qty,
                "price": product["price"],
                "subtotal": subtotal
            })
            
            self.bill_tree.insert("", "end", values=(
                product["name"], 
                qty, 
                f"₹{product['price']:.2f}", 
                f"₹{subtotal:.2f}"
            ))
            
            self.calculate_totals()
            self.product_id_entry.delete(0, tk.END)
            self.quantity_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def calculate_totals(self):
        subtotal = sum(item["subtotal"] for item in self.current_items)
        tax = subtotal * 0.05  # 5% tax
        total = subtotal + tax
        
        self.summary_label.config(
            text=f"Subtotal: ₹{subtotal:.2f} | Tax: ₹{tax:.2f} | Total: ₹{total:.2f}"
        )
    
    def clear_all(self):
        self.current_items = []
        self.bill_tree.delete(*self.bill_tree.get_children())
        self.customer_entry.delete(0, tk.END)
        self.summary_label.config(text="Subtotal: ₹0.00 | Tax: ₹0.00 | Total: ₹0.00")
    
    def confirm_generate_bill(self):
        if not self.current_items:
            messagebox.showwarning("Warning", "No items in the bill.")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to generate this bill?"):
            self.generate_bill()
    
    def generate_bill(self):
        now = datetime.now()
        bill_id = str(uuid.uuid4())[:8].upper()
        subtotal = sum(item["subtotal"] for item in self.current_items)
        tax = subtotal * 0.05
        total = subtotal + tax
        customer = self.customer_entry.get() or "Walk-in Customer"
        
        bills = load_bills()
        
        for item in self.current_items:
            new_bill = {
                "bill_id": bill_id,
                "date": now.strftime("%Y-%m-%d %H:%M"),
                "product": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "subtotal": round(item["subtotal"], 2),
                "tax": round(item["subtotal"] * 0.05, 2),
                "total": round(item["subtotal"] * 1.05, 2),
                "customer": customer
            }
            bills = pd.concat([bills, pd.DataFrame([new_bill])])
        
        save_bills(bills)
        
        # Update inventory
        inv = load_inventory()
        for item in self.current_items:
            inv.loc[inv["product_id"] == item["product_id"], "quantity"] -= item["quantity"]
        save_inventory(inv)
        
        # Generate receipt
        receipt_window = tk.Toplevel(self.top)
        receipt_window.title(f"Receipt - {bill_id}")
        receipt_window.geometry("400x600")
        
        receipt_text = ScrolledText(receipt_window, wrap=tk.WORD, font=("Courier", 10))
        receipt_text.pack(fill="both", expand=True)
        
        receipt = f"{'INVOICE':^40}\n"
        receipt += f"{'-'*40}\n"
        receipt += f"Bill ID: {bill_id}\n"
        receipt += f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n"
        receipt += f"Customer: {customer}\n"
        receipt += f"{'-'*40}\n"
        receipt += f"{'Item':<20}{'Qty':>5}{'Price':>10}{'Total':>10}\n"
        receipt += f"{'-'*40}\n"
        
        for item in self.current_items:
            receipt += f"{item['name'][:18]:<20}{item['quantity']:>5}₹{item['price']:>9.2f}₹{item['subtotal']:>9.2f}\n"
        
        receipt += f"{'-'*40}\n"
        receipt += f"{'Subtotal:':<30}₹{subtotal:>9.2f}\n"
        receipt += f"{'Tax (5%):':<30}₹{tax:>9.2f}\n"
        receipt += f"{'-'*40}\n"
        receipt += f"{'TOTAL:':<30}₹{total:>9.2f}\n"
        receipt += f"{'-'*40}\n"
        receipt += f"{'Thank you for shopping with us!':^40}\n"
        
        receipt_text.insert(tk.END, receipt)
        receipt_text.config(state="disabled")
        
        ttk.Button(receipt_window, text="Print", command=lambda: print_receipt(receipt),
                  style="Billing.TButton").pack(pady=5)
        ttk.Button(receipt_window, text="Close", command=receipt_window.destroy,
                  style="Billing.TButton").pack(pady=5)
        
        self.clear_all()
        refresh_inventory_table()
        show_low_stock_badge()

# ==============================================
# Main Functions
# ==============================================
def add_stock_ui():
    try:
        pid = int(product_id_entry.get())
        qty = int(quantity_entry.get())
        inv = load_inventory()

        if pid in inv["product_id"].values:
            inv.loc[inv["product_id"] == pid, "quantity"] += qty
            save_inventory(inv)
            messagebox.showinfo("Stock Updated", f"Added {qty} units.")
            refresh_inventory_table()
            show_low_stock_badge()
        else:
            messagebox.showerror("Error", "Product not found.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def add_new_product():
    try:
        name = simpledialog.askstring("Product Name", "Enter name:")
        if not name:
            return
            
        qty = int(simpledialog.askstring("Quantity", "Enter quantity:", initialvalue="0"))
        price = float(simpledialog.askstring("Price", "Enter price:", initialvalue="0.00"))
        min_stock = int(simpledialog.askstring("Minimum Stock", "Enter minimum stock level:", initialvalue="5"))

        inv = load_inventory()
        pid = inv["product_id"].max() + 1 if not inv.empty else 1
        inv = pd.concat([inv, pd.DataFrame([{
            "product_id": pid, 
            "name": name, 
            "quantity": qty, 
            "price": price,
            "min_stock": min_stock
        }])])
        save_inventory(inv)
        messagebox.showinfo("Success", f"{name} added.")
        refresh_inventory_table()
        show_low_stock_badge()
    except:
        messagebox.showerror("Error", "Invalid input.")

def on_search(event):
    search_txt = search_entry.get()
    refresh_inventory_table(search_txt)

def show_selected_chart():
    txn = load_transactions()
    inv = load_inventory()
    txn["date"] = pd.to_datetime(txn["date"])
    txn["day_of_week"] = txn["date"].dt.day_name()
    chart_type = chart_var.get()

    plt.figure(figsize=(8, 5))
    
    if chart_type == "Sales by Day":
        data = txn.groupby("day_of_week")["quantity_sold"].sum().reindex([
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ])
        data.plot(kind="bar", color="skyblue", title="Sales by Day")
    elif chart_type == "Top Products":
        prod = txn.groupby("product_id")["quantity_sold"].sum()
        prod.index = prod.index.map(lambda x: inv.loc[inv["product_id"] == x, "name"].values[0])
        prod.sort_values(ascending=False).head(10).plot(kind="bar", title="Top Products")
    elif chart_type == "Sales Heatmap":
        pivot = txn.pivot_table(index="day_of_week", columns="product_id", values="quantity_sold", aggfunc="sum", fill_value=0)
        pid_name_map = dict(zip(inv["product_id"], inv["name"]))
        pivot.rename(columns=pid_name_map, inplace=True)
        pivot = pivot.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        sns.heatmap(pivot, annot=True, fmt=".2f", cmap="YlGnBu")
        plt.title("Sales Heatmap")
        plt.xlabel("Products")
        plt.ylabel("Days of the Week")
    
    plt.tight_layout()
    plt.show()

def view_bills():
    bills = load_bills()
    if bills.empty:
        messagebox.showinfo("Info", "No bills found.")
        return
    
    bills_window = tk.Toplevel()
    bills_window.title("Bill History")
    bills_window.geometry("800x600")
    
    search_frame = ttk.Frame(bills_window)
    search_frame.pack(pady=10, padx=10, fill="x")
    
    ttk.Label(search_frame, text="Search Bills:").pack(side="left")
    search_entry = ttk.Entry(search_frame)
    search_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    tree_frame = ttk.Frame(bills_window)
    tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
    
    columns = ["Bill ID", "Date", "Customer", "Product", "Quantity", "Total"]
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="center")
    
    tree.column("Date", width=150)
    tree.column("Customer", width=150)
    tree.column("Product", width=200)
    
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    def populate_tree(data):
        tree.delete(*tree.get_children())
        if data.empty:
            messagebox.showinfo("Info", "No bills found.")
            return
        for _, row in data.iterrows():
            tree.insert("", "end", values=(
                row.get("bill_id", "N/A"),
                row.get("date", "N/A"),
                row.get("customer", "N/A"),
                row.get("product", "N/A"),
                row.get("quantity", "N/A"),
                f"₹{row.get('total', 0):.2f}"
            ))

    
    populate_tree(bills)
    
    def on_search():
        query = search_entry.get().lower()
        if not query:
            filtered = bills
        else:
            filtered = bills[
                bills["bill_id"].str.contains(query, case=False) |
                bills["customer"].str.contains(query, case=False) |
                bills["product"].str.contains(query, case=False)
            ]
        populate_tree(filtered)
    
    search_entry.bind("<KeyRelease>", lambda e: on_search())
    
    ttk.Button(bills_window, text="Close", command=bills_window.destroy).pack(pady=10)

def export_report():
    try:
        report_type = simpledialog.askstring("Export Report", 
                                           "Enter 'sales' for sales report or 'inventory' for inventory report:")
        if not report_type:
            return
            
        if report_type == 'sales':
            data = load_transactions()
            filename = "sales_report.csv"
        elif report_type == 'inventory':
            data = load_inventory()
            filename = "inventory_report.csv"
        else:
            messagebox.showerror("Error", "Invalid report type.")
            return
        
        data.to_csv(filename, index=False)
        messagebox.showinfo("Success", f"Report exported as {filename}")
        webbrowser.open(filename)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def generate_purchase_order(low_stock):
    now = datetime.now()
    supplier = simpledialog.askstring("Purchase Order", "Enter supplier name:")
    if not supplier:
        return
    
    delivery_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    
    po_window = tk.Toplevel()
    po_window.title("Purchase Order")
    po_window.geometry("500x400")
    
    po_text = ScrolledText(po_window, wrap=tk.WORD, font=("Courier", 10))
    po_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    po = f"{'PURCHASE ORDER':^40}\n"
    po += f"{'-'*40}\n"
    po += f"Date: {now.strftime('%Y-%m-%d')}\n"
    po += f"Supplier: {supplier}\n"
    po += f"Delivery By: {delivery_date}\n"
    po += f"{'-'*40}\n"
    po += f"{'ID':<5}{'Product':<20}{'Qty':>5}{'Price':>10}\n"
    po += f"{'-'*40}\n"
    
    total = 0
    for _, row in low_stock.iterrows():
        needed = row["min_stock"] - row["quantity"]
        po += f"{row['product_id']:<5}{row['name'][:18]:<20}{needed:>5}₹{row['price']:>9.2f}\n"
        total += needed * row["price"]
    
    po += f"{'-'*40}\n"
    po += f"{'TOTAL:':<30}₹{total:>9.2f}\n"
    po += f"{'-'*40}\n"
    
    po_text.insert(tk.END, po)
    po_text.config(state="disabled")
    
    btn_frame = ttk.Frame(po_window)
    btn_frame.pack(pady=10)
    
    ttk.Button(btn_frame, text="Print", command=lambda: print_receipt(po)).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Close", command=po_window.destroy).pack(side="left", padx=5)

def print_receipt(content):
    """Simulate printing by saving to a text file and opening it"""
    filename = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w") as f:
        f.write(content)
    webbrowser.open(filename)

# ==============================================
# Main Application
# ==============================================
root = tk.Tk()
root.title("Python Inventory System")
root.geometry("800x700")
root.configure(bg="#f5f5f5")

# Configure styles
style = ttk.Style()
style.configure("TFrame", background="#f5f5f5")
style.configure("TLabel", background="#f5f5f5", font=("Arial", 10))
style.configure("TButton", font=("Arial", 10), padding=5)
style.configure("Warning.TButton", foreground="red", font=("Arial", 10, "bold"))
style.configure("Safe.TButton", foreground="green", font=("Arial", 10))
style.configure("Header.TLabel", font=("Arial", 14, "bold"))

# Header Frame
header_frame = ttk.Frame(root, padding=10)
header_frame.pack(fill="x")

ttk.Label(header_frame, text="Python Inventory System", style="Header.TLabel").pack(side="left")
ttk.Label(header_frame, text=f"Date: {datetime.today().strftime('%Y-%m-%d')}", 
          style="TLabel").pack(side="right")

# Input Frame
input_frame = ttk.Frame(root, padding=10)
input_frame.pack(fill="x")

ttk.Label(input_frame, text="Product ID:").grid(row=0, column=0, padx=5)
product_id_entry = ttk.Entry(input_frame)
product_id_entry.grid(row=0, column=1, padx=5)

ttk.Label(input_frame, text="Quantity:").grid(row=0, column=2, padx=5)
quantity_entry = ttk.Entry(input_frame)
quantity_entry.grid(row=0, column=3, padx=5)

# Button Frame
button_frame = ttk.Frame(root, padding=10)
button_frame.pack(fill="x")

ttk.Button(button_frame, text="New Bill", command=lambda: BillingWindow(root)).pack(side="left", padx=5)
ttk.Button(button_frame, text="Add Stock", command=add_stock_ui).pack(side="left", padx=5)
ttk.Button(button_frame, text="New Product", command=add_new_product).pack(side="left", padx=5)
low_stock_btn = ttk.Button(button_frame, text="Inventory Healthy", style="Safe.TButton", 
                          command=lambda: LowStockDialog(root))
low_stock_btn.pack(side="left", padx=5)

# Search Frame
search_frame = ttk.Frame(root, padding=10)
search_frame.pack(fill="x")

search_entry = ttk.Entry(search_frame)
search_entry.pack(side="left", padx=5, fill="x", expand=True)
search_entry.insert(0, "Search products...")
search_entry.bind("<KeyRelease>", on_search)

# Inventory Tree Frame
tree_frame = ttk.Frame(root)
tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

inventory_tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Quantity", "Price"), show="headings")
inventory_tree.heading("ID", text="ID")
inventory_tree.heading("Name", text="Product Name")
inventory_tree.heading("Quantity", text="Quantity")
inventory_tree.heading("Price", text="Price")

inventory_tree.column("ID", width=50, anchor="center")
inventory_tree.column("Name", width=200)
inventory_tree.column("Quantity", width=100, anchor="center")
inventory_tree.column("Price", width=100, anchor="center")

scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=inventory_tree.yview)
inventory_tree.configure(yscrollcommand=scrollbar.set)

inventory_tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Chart Controls
chart_frame = ttk.Frame(root, padding=10)
chart_frame.pack(fill="x")

chart_var = tk.StringVar()
chart_options = ["Sales by Day", "Top Products", "Sales Heatmap"]
chart_menu = ttk.Combobox(chart_frame, textvariable=chart_var, values=chart_options, state="readonly")
chart_menu.set("Sales by Day")
chart_menu.pack(side="left", padx=5)

ttk.Button(chart_frame, text="Show Chart", command=show_selected_chart).pack(side="left", padx=5)
ttk.Button(chart_frame, text="View Bills", command=view_bills).pack(side="left", padx=5)
ttk.Button(chart_frame, text="Export Report", command=export_report).pack(side="left", padx=5)

# Footer
footer_frame = ttk.Frame(root, padding=10)
footer_frame.pack(fill="x", side="bottom")

ttk.Label(footer_frame, text=f"© {datetime.today().year} Python Inventory System", 
          style="TLabel").pack(side="right")

# Initial setup
refresh_inventory_table()
show_low_stock_badge()

root.mainloop()

                                