name: Run Scraper

on:
  workflow_dispatch:
  push:
    branches:
      - main
  schedule:
    - cron: '0 * * * *'  # كل ساعة

jobs:
  run-scraper:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run main.py
      env:
        ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
        DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
      run: python main.py

    - name: Run Profile.py
      env:
        ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
        DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
      run: python Profile.py
       
    - name: رفع page.html
      uses: actions/upload-artifact@v4
      with:
        name: page
        path: page.html

    - name: رفع episode_debug.html
      uses: actions/upload-artifact@v4
      with:
        name: episode_debug
        path: episode_debug.html
