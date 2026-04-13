#!/bin/bash

# Update Sidebar.jsx (this was already partially correct but ensuring consistency)
# Note: Sidebar.jsx already has aria-label on line 20-25 via `aria-label={item.label}` so no need to fix it here

# Update TopNavbar.jsx (add aria-label to tabs)
sed -i 's/<button/<button aria-label={tab.label}/' visual_hq/src/components/TopNavbar.jsx

# Remove the .orig and .patch files, we don't want to process them
rm -f visual_hq/src/components/*.orig visual_hq/src/components/*.patch visual_hq/src/components/*.rej
