# Hiboutik / Odoo 16 POS Connector

This addon is under development do not use in production

http://www.hiboutik.fr

https://www.odoo.com

Available features:
-------------------
 - Sync Products Categories (Hiboutik --> Odoo 16)
 - Sync POS Products Categories (Hiboutik --> Odoo 16)
 - Sync Products (Hiboutik --> Odoo 16)
 - Sync Sales (Hiboutik --> Odoo 16)
 - Sync Closed Sales Payments (Hiboutik --> Odoo 16)
 - Sync Customers (Hiboutik --> Odoo 16)
 - Sync Floor (Hiboutik --> Odoo 16)
 - Sync Ressources "Tables" (Hiboutik --> Odoo 16)

Roadmap under development
-------------------------
 - Sync Categories (Hiboutik <--> Odoo 16)
 - Sync Products (Hiboutik <--> Odoo 16)


# IMPORTANT

After installation, you must indicate the tax ID in Odoo that correspond to those of HIBOUTIK before first sync
 - In Hiboutik go to Settings > Taxes and note taxes IDS
 - In Odoo go to Accounting > Settings > Taxes and write in each tax the correspondence of the Hiboutik Taxe ID in the "Hiboutik tax Id" field
 - In Odoo POS Payments indiquate Hiboutik payment code. Write Hiboutik Payment Type field "eg: In Hiboutik Credit Card is CB, write in Odoo Payment Methode CB"

In POS Config (Odoo field "Hiboutik Store ID") indiquate Hiboutik store ID

This module is created for a restaurant, improvements are welcome

During development, synchronization must be done manually from each company (Hiboutik tab) in general settings.
When we have a stable version we will add a cron job

----------
## License
This repository is licensed under [AGPL-3.0](LICENSE).

## Author
(https://github.com/zuher83)
