# Hiboutik / Odoo 14 POS Connector

This addon is under development do not use in production

Available features:
-------------------
 - Sync Categories (Hiboutik --> Odoo 14)
 - Sync Products (Hiboutik --> Odoo 14)

Roadmap under development
-------------------------
 - Sync Sales (Hiboutik --> Odoo 14)
 - Sync Categories (Hiboutik <--> Odoo 14)
 - Sync Products (Hiboutik <--> Odoo 14)


# IMPORTANT

After installation, you must indicate the tax ID in Odoo that correspond to those of HIBOUTIK before first sync
 - In Hiboutik go to Settings > Taxes and note taxes IDS
 - In Odoo go to Accounting > Settings > Taxes and write in each tax the correspondence of the Hiboutik Taxe ID in the "Hiboutik tax Id" field

 This module is created for a restaurant, improvements are welcome

During development, synchronization must be done manually from each company (Hiboutik tab) in general settings.
When we have a stable version we will add a cron job

----------
## License
This repository is licensed under [AGPL-3.0](LICENSE).

## Author
(https://github.com/zuher83)
