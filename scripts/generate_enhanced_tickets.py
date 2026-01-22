#!/usr/bin/env python3
"""
Enhanced Synthetic Ticket Generator for RAG-KG System.
Generates tickets with complex intra-issue structures (description, steps, resolution)
and inter-issue relations (explicit references, semantic clustering).
"""

import json
import random
import os
from pathlib import Path
from datetime import datetime, timedelta

# Constants for generation
PRODUCTS = ["LinkedIn Mobile", "LinkedIn Desktop", "LinkedIn APIs", "Ads Manager", "Premium Subscriptions"]
ISSUE_TYPES = ["Authentication", "Performance", "UI/UX", "Data Sync", "Billing"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Resolved", "Closed", "Work-in-Progress"]

# Templates for realistic content
PROBLEM_SCENARIOS = [
    {
        "category": "Authentication",
        "title": "Password reset email not received for {product} users",
        "desc": "Users on {product} are reporting that they do not receive the password reset token via email after {action}. This seems to affect users with @gmail.com domains primarily.",
        "steps": "1. Go to login page\n2. Click 'Forgot Password'\n3. Enter email address\n4. Wait for email (never arrives)",
        "resolution": "Increased the timeout for SMTP relay and updated the whitelist for Gmail servers.",
        "tags": ["email", "auth", "token"]
    },
    {
        "category": "Performance",
        "title": "High latency when loading dashboard in {product}",
        "desc": "The dashboard page on {product} takes more than 10 seconds to load during peak hours. Investigation shows slow DB queries on the {feature} table.",
        "steps": "1. Log in to dashboard\n2. Select time range 'Last 30 Days'\n3. Observe spinner for >10s",
        "resolution": "Added composite index to the {feature} table and implemented Redis caching for common dashboard queries.",
        "tags": ["latency", "db", "performance"]
    },
    {
        "category": "Data Sync",
        "title": "Contact sync failed between {product} and mobile device",
        "desc": "Contacts updated on {product} are not reflecting on the mobile app. Error 502 returned during sync phase.",
        "steps": "1. Update a contact name on {product}\n2. Refresh mobile app\n3. Check if name is updated",
        "resolution": "Fixed a protocol mismatch in the sync worker that was causing data truncation.",
        "tags": ["sync", "mobile", "error_502"]
    }
]

FEATURES = ["Profile View", "Search Service", "Feed Engine", "Analytics Dashboard", "Messaging"]
AUTHORS = ["Support_Alice", "Engineering_Bob", "User_Charlie", "Ops_Dave"]

def generate_ticket(ticket_id):
    scenario = random.choice(PROBLEM_SCENARIOS)
    product = random.choice(PRODUCTS)
    feature = random.choice(FEATURES)
    
    title = scenario["title"].format(product=product, feature=feature)
    description = scenario["desc"].format(product=product, feature=feature, action="requesting reset")
    steps = scenario["steps"]
    resolution = scenario["resolution"].format(feature=feature)
    
    # Generate random comments
    num_comments = random.randint(2, 5)
    comments = []
    for i in range(num_comments):
        comments.append({
            "author": random.choice(AUTHORS),
            "text": f"Found a similar issue in {random.choice(PRODUCTS)}. Investigating if logs match.",
            "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat()
        })
        
    ticket = {
        "ticket_id": f"TIC-{ticket_id}",
        "title": title,
        "description": description,
        "steps_to_reproduce": steps,
        "resolution": resolution,
        "product": product,
        "priority": random.choice(PRIORITIES),
        "status": random.choice(STATUSES),
        "created_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "tags": scenario["tags"] + [product.lower().replace(" ", "-")],
        "comments": comments,
        "entities": {
            "products": [product],
            "features": [feature],
            "errors": ["502" if "502" in scenario["tags"] else "None"]
        }
    }
    
    # Add an explicit reference occasionally
    if ticket_id > 100 and random.random() > 0.7:
        ref_id = random.randint(100, ticket_id - 1)
        ticket["entities"]["references"] = [f"TIC-{ref_id}"]
        ticket["description"] += f" (Related to TIC-{ref_id})"
        
    return ticket

def main():
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    count = 100  # Generate 100 high-quality tickets
    print(f"Generating {count} enhanced tickets in {output_dir.absolute()}...")
    
    for i in range(101, 101 + count):
        ticket = generate_ticket(i)
        with open(output_dir / f"{ticket['ticket_id']}.json", "w", encoding="utf-8") as f:
            json.dump(ticket, f, indent=2)
            
    print("Generation complete!")

if __name__ == "__main__":
    main()
