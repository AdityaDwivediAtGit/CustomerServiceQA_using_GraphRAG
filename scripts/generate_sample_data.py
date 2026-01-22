#!/usr/bin/env python3
"""
Sample Ticket Data Generator for RAG-KG Customer Service QA System

Generates synthetic customer service tickets in Jira-like format for testing
the knowledge graph construction pipeline.
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Sample data templates
PRODUCTS = ["Mobile App", "Web Portal", "API", "Desktop Client", "Mobile Website"]
ISSUES = [
    "Login issues", "Password reset problems", "Payment failures", "Data sync errors",
    "UI crashes", "Slow performance", "Feature not working", "Account locked",
    "Email notifications", "File upload issues", "Search not working", "Permission errors"
]
STATUSES = ["open", "in_progress", "resolved", "closed"]
PRIORITIES = ["low", "medium", "high", "critical"]
TAGS = ["bug", "feature", "enhancement", "security", "performance", "ui", "api", "mobile", "web"]

def generate_random_date(start_date, end_date):
    """Generate a random date between start and end dates."""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + timedelta(days=random_days)

def generate_comments(ticket_id, num_comments=3):
    """Generate sample comments for a ticket."""
    comments = []
    base_time = generate_random_date(
        datetime(2024, 1, 1),
        datetime(2024, 12, 31)
    )

    for i in range(num_comments):
        author = "user" if i % 2 == 0 else "agent"
        text_options = [
            f"Having trouble with {random.choice(ISSUES).lower()}",
            "Can you help me resolve this?",
            "Tried clearing cache, still not working",
            "This is affecting multiple users",
            "Urgent - production issue",
            "Please provide update on this ticket",
            "Issue resolved, thank you!",
            "Still experiencing the problem"
        ]
        comment = {
            "author": author,
            "text": random.choice(text_options),
            "timestamp": (base_time + timedelta(hours=i*2)).isoformat() + "Z"
        }
        comments.append(comment)

    return comments

def generate_ticket(ticket_id, base_date):
    """Generate a single ticket with all required fields."""
    product = random.choice(PRODUCTS)
    issue = random.choice(ISSUES)
    title = f"{issue} with {product}"

    # Generate description
    descriptions = [
        f"Users are experiencing {issue.lower()} when using the {product.lower()}. This is impacting customer satisfaction.",
        f"Multiple reports of {issue.lower()} in the {product.lower()}. Need immediate attention.",
        f"Critical issue: {issue.lower()} affecting {product.lower()} functionality.",
        f"Customer reported {issue.lower()} with {product.lower()}. Unable to proceed with normal operations."
    ]
    description = random.choice(descriptions)

    # Generate resolution if status is resolved/closed
    status = random.choice(STATUSES + ["resolved"] * 3)  # Bias towards resolved
    resolution = None
    if status in ["resolved", "closed"]:
        resolutions = [
            "Cleared application cache and restarted services",
            "Updated configuration settings",
            "Applied security patch",
            "Fixed database connection issue",
            "Updated user permissions",
            "Resolved by engineering team",
            "Issue was in third-party integration"
        ]
        resolution = random.choice(resolutions)

    # Generate tags
    num_tags = random.randint(1, 3)
    ticket_tags = random.sample(TAGS, num_tags)

    ticket = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "product": product,
        "status": status,
        "priority": random.choice(PRIORITIES),
        "created_date": base_date.isoformat(),
        "updated_date": (base_date + timedelta(days=random.randint(1, 30))).isoformat(),
        "comments": generate_comments(ticket_id),
        "resolution": resolution,
        "tags": ticket_tags,
        "assignee": f"agent_{random.randint(1, 10)}",
        "reporter": f"user_{random.randint(1, 100)}"
    }

    return ticket

def main():
    parser = argparse.ArgumentParser(description="Generate sample ticket data")
    parser.add_argument("--num_tickets", type=int, default=100, help="Number of tickets to generate")
    parser.add_argument("--output_dir", type=str, default="data/raw", help="Output directory for tickets")
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.num_tickets} sample tickets...")

    # Generate tickets
    base_start = datetime(2024, 1, 1)
    base_end = datetime(2024, 12, 31)

    for i in range(args.num_tickets):
        ticket_id = "04d"
        base_date = generate_random_date(base_start, base_end)

        ticket = generate_ticket(ticket_id, base_date)

        # Save to file
        filename = f"{ticket_id}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(ticket, f, indent=2, ensure_ascii=False)

        if (i + 1) % 10 == 0:
            print(f"Generated {i + 1}/{args.num_tickets} tickets...")

    print(f"Sample data generation complete!")
    print(f"Tickets saved to: {output_dir.absolute()}")
    print(f"Total files: {args.num_tickets}")

if __name__ == "__main__":
    main()