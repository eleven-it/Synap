# User Manual - Sales Module
## Synap System

---

## Table of Contents

1. [Introduction](#introduction)
2. [Module Access](#module-access)
3. [Sales Dashboard](#sales-dashboard)
4. [Customer Management](#customer-management)
5. [Sales Order Management](#sales-order-management)
6. [Invoice Management](#invoice-management)
7. [Payment Management](#payment-management)
8. [Delivery Management](#delivery-management)
9. [Return Management](#return-management)
10. [Credit Note Management](#credit-note-management)
11. [Configuration](#configuration)
12. [Reports](#reports)
13. [Inventory Integration](#inventory-integration)
14. [Workflows](#workflows)
15. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

The Sales module of Synap is a complete solution for managing your company's commercial cycle. It allows you to manage customers, create and manage sales orders, invoice, process payments, manage deliveries, and generate detailed reports.

### Main Features

- **Complete customer management** with contact information and credit limits
- **Sales orders** with automated states and stock validation
- **Automatic invoicing** with different document types
- **Payment management** with multiple payment methods
- **Delivery control** with inventory integration
- **Returns and credit notes** to manage incidents
- **Detailed reports** for commercial analysis
- **Inventory integration** for real-time stock control

---

## 2. Module Access

### 2.1 Main Navigation

1. Access the Synap system with your credentials
2. In the main menu, click on **"Sales"**
3. You will be directed to the Sales Dashboard

### 2.2 Required Permissions

To access the sales module, you need the following permissions:
- `sales.view_salesorder` - View sales orders
- `sales.add_salesorder` - Create sales orders
- `sales.change_salesorder` - Edit sales orders
- `sales.delete_salesorder` - Delete sales orders

---

## 3. Sales Dashboard

### 3.1 Overview

The Sales Dashboard provides a complete view of your commercial operation status:

#### Statistics Cards
- **Total Customers**: Total number of registered customers
- **Total Orders**: Number of sales orders
- **Total Invoices**: Number of issued invoices
- **Total Payments**: Number of processed payments

#### Charts and Tables
- **Orders by Status**: Distribution of orders according to their current status
- **Recent Sales**: Latest processed orders
- **Top Customers**: Top customers by sales volume

### 3.2 Quick Actions

From the dashboard you can quickly access:
- **New Customer**: Create a new customer
- **New Order**: Create a sales order
- **View All**: Access complete lists of each entity

---

## 4. Customer Management

### 4.1 Customer List

**Access**: Sales → Customers

The list shows:
- Customer name
- Type (Company or Person)
- Email and phone
- Status (Active/Inactive)
- Credit limit
- Origin (Manual, E-commerce, etc.)

#### Available Filters
- By customer type
- By status
- By origin
- By credit limit

### 4.2 Create New Customer

**Access**: Dashboard → New Customer

#### Required Fields
- **Name**: Full name or company name
- **Type**: Company or Person
- **Email**: Email address (optional)
- **Phone**: Contact number (optional)
- **VAT**: For Argentine companies (optional)

#### Optional Fields
- **Credit Limit**: Maximum available credit amount
- **Origin**: How the customer was registered
- **TiendaNube Customer ID**: For e-commerce integration

### 4.3 Edit Customer

1. In the customer list, click on the customer name
2. Click **"Edit"**
3. Modify the necessary fields
4. Save changes

### 4.4 Contact Management

Each customer can have multiple contacts:

#### Add Contact
1. In the customer detail, go to the "Contacts" section
2. Click **"Add Contact"**
3. Complete:
   - Contact name
   - Email
   - Phone
   - Mark as primary contact (optional)

#### Edit/Delete Contacts
- Use action buttons on each contact
- You can only delete non-primary contacts

---

## 5. Sales Order Management

### 5.1 Order States

Sales orders follow a specific state flow:

1. **Draft**: Order in creation
2. **Quotation Sent**: Quotation sent to customer
3. **Confirmed**: Customer confirms the order
4. **In Process**: Preparing the order
5. **Ready to Deliver**: Order prepared
6. **Partially Delivered**: Partial delivery
7. **Delivered**: Completely delivered
8. **Invoiced**: Invoice created
9. **Paid**: Payment received
10. **Completed**: Order finalized
11. **Cancelled**: Order cancelled

### 5.2 Create New Order

**Access**: Dashboard → New Order

#### Step 1: General Information
- **Customer**: Select the order customer
- **Branch**: Branch where the order is processed
- **Order Date**: Creation date
- **Payment Terms**: Payment terms
- **Price List**: Price list to apply
- **Seller**: User responsible for the sale

#### Step 2: Order Lines
- **Product**: Select product from the list
- **Quantity**: Requested quantity
- **Unit Price**: Price per unit
- **Discount**: Discount percentage (optional)
- **Description**: Additional notes (optional)

#### Automatic Validations
- **Available Stock**: System validates stock in real time
- **Credit Limit**: Verifies customer limit
- **Prices**: Applies selected price list

### 5.3 Manage Order States

#### Confirm Order
1. In the order detail, click **"Confirm"**
2. The system:
   - Validates stock availability
   - Automatically reserves stock
   - Changes state to "Confirmed"

#### Process Order
1. Click **"In Process"**
2. Order goes to preparation

#### Mark Ready to Deliver
1. Click **"Ready to Deliver"**
2. Order is prepared for delivery

#### Deliver Order
1. Click **"Deliver"**
2. The system:
   - Automatically creates stock movements
   - Marks order as delivered

### 5.4 Edit Order

#### When it can be edited
- Only in "Draft" or "Quotation Sent" state
- Confirmed orders require previous cancellation

#### Allowed Modifications
- Change customer (if no invoices)
- Modify order lines
- Adjust prices and discounts
- Change payment terms

### 5.5 Cancel Order

1. In the order detail, click **"Cancel"**
2. Enter cancellation reason
3. The system:
   - Releases stock reservations
   - Marks order as cancelled
   - Records cancellation in log

---

## 6. Invoice Management

### 6.1 Create Invoice from Order

**Access**: Order Detail → "Create Invoice"

#### Automatic Invoicing
- System pre-fills order information
- Includes all order lines
- Applies order prices and discounts

#### Invoice Types
- **Invoice A**: For final consumers
- **Invoice B**: For companies with VAT
- **Invoice C**: For export

### 6.2 Manual Invoice Management

#### Create Manual Invoice
1. Sales → Invoices → New Invoice
2. Complete required information
3. Add invoice lines

#### Edit Invoice
- Only invoices in "Draft" state
- Sent invoices cannot be modified

### 6.3 Invoice States

- **Draft**: In creation
- **Sent**: Sent to customer
- **Paid**: Payment received
- **Cancelled**: Invoice cancelled

---

## 7. Payment Management

### 7.1 Record Payment

#### From Invoice
1. In the invoice detail, click **"Record Payment"**
2. Complete:
   - Payment date
   - Amount
   - Payment method
   - Reference (optional)

#### Manual Payment
1. Sales → Payments → New Payment
2. Associate with invoice or order
3. Complete payment information

### 7.2 Payment Methods

- **Cash**
- **Bank Transfer**
- **Check**
- **Credit Card**
- **Debit Card**
- **Mercado Pago**
- **Others**

### 7.3 Payment Reconciliation

- Payments are automatically associated with invoices
- You can manually adjust the association
- System calculates pending balances

---

## 8. Delivery Management

### 8.1 Create Delivery Order

#### From Order
1. In the order detail, click **"Create Delivery"**
2. System pre-fills information
3. Select source warehouse
4. Confirm delivery

#### Manual Delivery
1. Sales → Deliveries → New Delivery
2. Associate with an order
3. Complete delivery information

### 8.2 Process Delivery

1. In the delivery detail, click **"Process"**
2. The system:
   - Validates available stock
   - Creates inventory movements
   - Updates order status

### 8.3 Delivery States

- **Draft**: In creation
- **Confirmed**: Ready to process
- **Processed**: Delivery completed
- **Cancelled**: Delivery cancelled

---

## 9. Return Management

### 9.1 Create Return

#### From Delivery
1. In the delivery detail, click **"Create Return"**
2. Select products to return
3. Specify quantity and reason

#### Manual Return
1. Sales → Returns → New Return
2. Associate with order and delivery
3. Complete information

### 9.2 Return Types

- **Product Defect**: Product with faults
- **Delivery Error**: Incorrect product
- **Customer Change of Mind**: Customer changes opinion
- **Others**: Other reasons

### 9.3 Process Return

1. Approve the return
2. The system:
   - Creates stock return movements
   - Updates inventory
   - Generates credit note (optional)

---

## 10. Credit Note Management

### 10.1 Create Credit Note

#### From Invoice
1. In the invoice detail, click **"Create Credit Note"**
2. Select lines to cancel
3. Specify reason

#### Manual Credit Note
1. Sales → Credit Notes → New Note
2. Associate with invoice and order
3. Complete information

### 10.2 Apply Credit Note

1. In the note detail, click **"Apply"**
2. Select invoice to apply to
3. System automatically adjusts amounts

---

## 11. Configuration

### 11.1 Price Lists

#### Create Price List
1. Sales → Configuration → Price Lists
2. Complete:
   - List name
   - Currency
   - Validity dates
   - Products and prices

#### Manage List Items
- Add specific products
- Define prices by quantity
- Configure discounts
- Set promotional codes

### 11.2 Payment Terms

#### Create Payment Term
1. Sales → Configuration → Payment Terms
2. Define:
   - Term name
   - Description
   - Payment lines (percentages and days)

#### Term Examples
- **Cash**: 100% at the moment
- **30 days**: 100% at 30 days
- **50/50**: 50% at the moment, 50% at 30 days

---

## 12. Reports

### 12.1 Reports Dashboard

**Access**: Sales → Reports

#### Available Reports
- **Sales Summary**: Sales by period
- **Customer Analysis**: Performance by customer
- **Product Performance**: Best selling products

### 12.2 Sales Summary

#### Filters
- Time period
- Branch
- Seller
- Customer
- Order status

#### Metrics
- Total sales
- Number of orders
- Average per order
- Best selling products

### 12.3 Customer Analysis

- Sales by customer
- Purchase frequency
- Average value per customer
- Customers with highest growth

### 12.4 Product Performance

- Best selling products
- Margin per product
- Inventory turnover
- Low performance products

---

## 13. Inventory Integration

### 13.1 Automatic Stock Validation

The system automatically validates stock availability:

#### When Confirming Order
- Verifies available stock in branch
- Automatically reserves stock
- Prevents sales without stock

#### When Delivering Order
- Automatically creates stock movements
- Updates inventory in real time
- Maintains complete traceability

### 13.2 Stock States

#### Available
- Physical stock available for sale
- Not reserved for other orders

#### Reserved
- Stock reserved for confirmed orders
- Not available for new sales

#### In Transit
- Stock in delivery process
- Pending confirmation

### 13.3 Stock Alerts

#### Low Stock
- Alert when stock is below minimum
- Automatic notification when confirming orders

#### No Stock
- Automatic sales blocking
- Restocking suggestion

---

## 14. Workflows

### 14.1 Complete Sales Flow

#### 1. Create Customer
- Register customer information
- Set credit limit
- Add contacts

#### 2. Create Order
- Select customer
- Add products
- Apply prices and discounts

#### 3. Confirm Order
- Validate available stock
- Automatically reserve stock
- Change state to "Confirmed"

#### 4. Process Order
- Prepare products
- Change state to "In Process"

#### 5. Deliver
- Create delivery order
- Process delivery
- Update inventory

#### 6. Invoice
- Create invoice from order
- Send to customer

#### 7. Collect
- Record payment
- Update balances

### 14.2 Return Flow

#### 1. Create Return
- Associate with delivery
- Specify products and quantities
- Indicate reason

#### 2. Approve Return
- Validate information
- Process stock return

#### 3. Create Credit Note
- Generate credit note
- Apply to corresponding invoice

---

## 15. Troubleshooting

### 15.1 Common Errors

#### "Insufficient Stock"
**Problem**: Not enough stock to confirm order
**Solution**:
1. Check stock in inventory
2. Restock missing products
3. Adjust order quantities

#### "Credit Limit Exceeded"
**Problem**: Order exceeds customer credit limit
**Solution**:
1. Review customer credit limit
2. Request authorization for override
3. Adjust order amounts

#### "Order Cannot Be Edited"
**Problem**: Cannot modify a confirmed order
**Solution**:
1. Cancel current order
2. Create new order with corrections
3. Or request state change to draft

### 15.2 System Validations

#### Order Validations
- Customer must be active
- Stock must be available
- Credit limit must be respected
- Prices must be valid

#### Invoice Validations
- Order must be delivered
- Amounts must match
- Tax information must be correct

#### Payment Validations
- Invoice must exist
- Amount must not exceed balance
- Date must be valid

### 15.3 Support Contact

For technical problems or queries:
- **Email**: support@synap.com
- **Phone**: +54 11 1234-5678
- **Hours**: Monday to Friday 9:00 - 18:00

---

## Appendices

### A. Glossary of Terms

- **Sales Order**: Document that records customer purchase intention
- **Invoice**: Tax document that supports the sale
- **Delivery**: Physical process of product delivery
- **Stock Reservation**: Temporary inventory blocking for an order
- **Stock Movement**: Record of product input/output
- **Credit Note**: Document that cancels an invoice totally or partially

### B. Keyboard Shortcuts

- **Ctrl + N**: New order
- **Ctrl + C**: New customer
- **Ctrl + F**: Search
- **Ctrl + S**: Save
- **Esc**: Cancel operation

### C. State Codes

- **DRAFT**: Draft
- **CONFIRMED**: Confirmed
- **IN_PROCESS**: In Process
- **READY_TO_DELIVER**: Ready to Deliver
- **DELIVERED**: Delivered
- **INVOICED**: Invoiced
- **PAID**: Paid
- **COMPLETED**: Completed
- **CANCELLED**: Cancelled

---

*User Manual - Sales Module v1.0*
*Synap System - All rights reserved* 