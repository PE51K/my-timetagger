#!/usr/bin/env python3
"""
Streamlit app for Timetagger data visualization.

Run with: streamlit run app.py
Or with Docker: docker-compose up analytics
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import bcrypt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from db import TimetaggerDB


def load_credentials() -> dict:
    """
    Load credentials from .env file.
    Expected format: username:pass_hash (one per line)
    Note: bcrypt hashes contain $ characters, so we split only on the first colon.
    
    Returns:
        Dictionary mapping username to password hash
    """
    credentials = {}
    
    # Try to find .env file in project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_file = project_root / ".env"
    
    # Also check if ANALYTICS_CREDENTIALS or TIMETAGGER_CREDENTIALS env var is set
    env_creds = os.getenv("ANALYTICS_CREDENTIALS") or os.getenv("TIMETAGGER_CREDENTIALS")
    
    if env_creds:
        # Parse credentials from environment variable
        # Format: username1:hash1,username2:hash2 or username:hash
        for cred_line in env_creds.split(","):
            cred_line = cred_line.strip()
            if ":" in cred_line:
                # Split only on first colon to preserve hash with $ characters
                parts = cred_line.split(":", 1)
                if len(parts) == 2:
                    username = parts[0].strip()
                    pass_hash = parts[1].strip()
                    if username and pass_hash:
                        credentials[username] = pass_hash
    elif env_file.exists():
        # Read from .env file
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Split only on first colon to preserve hash with $ characters
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        username = parts[0].strip()
                        pass_hash = parts[1].strip()
                        # Don't strip the hash further - preserve all $ characters
                        if username and pass_hash:
                            credentials[username] = pass_hash
    
    return credentials


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Args:
        password: Plain text password
        password_hash: Bcrypt hash string (should start with $2a$, $2b$, or $2y$)
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        if not password or not password_hash:
            return False
        
        # Bcrypt hashes should start with $2a$, $2b$, or $2y$
        if not password_hash.startswith(("$2a$", "$2b$", "$2y$")):
            return False
        
        # Ensure password_hash is bytes for bcrypt
        if isinstance(password_hash, str):
            password_hash_bytes = password_hash.encode("utf-8")
        else:
            password_hash_bytes = password_hash
        
        # Verify password using bcrypt
        return bcrypt.checkpw(password.encode("utf-8"), password_hash_bytes)
    except Exception:
        return False


def check_authentication(username: str, password: str) -> bool:
    """
    Check if username and password are valid.
    
    Args:
        username: Username to check
        password: Password to check
        
    Returns:
        True if credentials are valid, False otherwise
    """
    credentials = load_credentials()
    
    if username not in credentials:
        return False
    
    stored_hash = credentials[username]
    return verify_password(password, stored_hash)


def show_login_page():
    """Display login page."""
    st.title("🔐 Login to Timetagger Analytics")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password.")
            elif check_authentication(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid username or password.")


def get_date_range_from_granularity(
    granularity: str, base_date: datetime
) -> Tuple[datetime, datetime]:
    """Get date range based on granularity."""
    if granularity == "days":
        start = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif granularity == "weeks":
        # Start of week (Monday)
        days_since_monday = base_date.weekday()
        start = (base_date - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(weeks=1)
    elif granularity == "months":
        start = base_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Next month
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        start = base_date
        end = base_date + timedelta(days=1)

    return start, end


def get_period_key(date: datetime, granularity: str) -> str:
    """Get a string key representing the time period for a given date."""
    if granularity == "days":
        return date.strftime("%Y-%m-%d")
    elif granularity == "weeks":
        # Get Monday of the week
        days_since_monday = date.weekday()
        monday = date - timedelta(days=days_since_monday)
        return monday.strftime("%Y-W%W")
    elif granularity == "months":
        return date.strftime("%Y-%m")
    else:
        return date.strftime("%Y-%m-%d")


def get_period_start_end(
    period_key: str, granularity: str
) -> Tuple[datetime, datetime]:
    """Get the start and end datetime for a given period key."""
    if granularity == "days":
        period_date = datetime.strptime(period_key, "%Y-%m-%d")
        start = period_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif granularity == "weeks":
        # Parse week format: YYYY-WWW
        year, week = period_key.split("-W")
        year = int(year)
        week = int(week)
        # Get first Monday of the year
        jan1 = datetime(year, 1, 1)
        days_offset = (7 - jan1.weekday()) % 7  # Days to first Monday
        first_monday = jan1 + timedelta(days=days_offset)
        # Calculate the Monday of the target week
        start = first_monday + timedelta(weeks=week - 1)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(weeks=1)
    elif granularity == "months":
        period_date = datetime.strptime(period_key, "%Y-%m")
        start = period_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        period_date = datetime.strptime(period_key, "%Y-%m-%d")
        start = period_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

    return start, end


def split_record_across_periods(
    record: dict, granularity: str
) -> List[Tuple[str, float]]:
    """
    Split a record across multiple periods if it spans them.

    Returns:
        List of tuples: [(period_key, duration_in_seconds)]
    """
    start_dt = record.get("datetime_start")
    end_dt = record.get("datetime_end")

    if not start_dt or not end_dt:
        # Fallback to single period
        period_key = get_period_key(start_dt or datetime.now(), granularity)
        return [(period_key, record.get("duration", 0))]

    result = []
    current_start = start_dt

    while current_start < end_dt:
        # Get period for current start time
        current_period_key = get_period_key(current_start, granularity)
        period_start, period_end = get_period_start_end(current_period_key, granularity)

        # Calculate overlap
        overlap_start = max(current_start, period_start)
        overlap_end = min(end_dt, period_end)

        if overlap_start < overlap_end:
            duration = (overlap_end - overlap_start).total_seconds()
            result.append((current_period_key, duration))

        # Move to next period
        current_start = period_end

    return result


def group_by_period_and_tags(records: List[dict], granularity: str) -> dict:
    """
    Group records by time period and level 1 tags.
    Splits records that span multiple periods.

    Returns:
        Dictionary: {period_key: {tag: total_duration}}
    """
    grouped = {}

    for record in records:
        if not record.get("datetime_start") or not record.get("datetime_end"):
            # Skip records without proper timestamps
            continue

        # Get level 1 tag (first tag or "No tags")
        tags = record.get("tags", [])
        tag = tags[0] if tags else "No tags"

        # Split record across periods
        period_splits = split_record_across_periods(record, granularity)

        for period_key, duration in period_splits:
            # Initialize if needed
            if period_key not in grouped:
                grouped[period_key] = {}
            if tag not in grouped[period_key]:
                grouped[period_key][tag] = 0

            # Add duration for this period
            grouped[period_key][tag] += duration

    return grouped


def group_by_tags_hierarchy(records: list[dict], max_depth: int) -> dict:
    """
    Group records by tag hierarchy.
    Returns nested dictionary structure: {tag1: {tag2: {tag3: duration}}}

    Args:
        records: List of parsed records
        max_depth: Maximum depth of tag hierarchy to consider

    Returns:
        Nested dictionary with tag hierarchy and total durations
    """
    hierarchy = {}

    for record in records:
        tags = record["tags"][:max_depth]  # Limit to max_depth
        duration = record["duration"]

        if not tags:
            # Records without tags go to "No tags"
            if "No tags" not in hierarchy:
                hierarchy["No tags"] = {}
            hierarchy["No tags"]["_total"] = (
                hierarchy["No tags"].get("_total", 0) + duration
            )
            continue

        # Build nested structure
        current = hierarchy
        for i, tag in enumerate(tags):
            if tag not in current:
                current[tag] = {}
            if i == len(tags) - 1:
                # Last tag, add duration
                current[tag]["_total"] = current[tag].get("_total", 0) + duration
            else:
                # Intermediate tag, continue nesting
                if "_total" not in current[tag]:
                    current[tag]["_total"] = 0
            current = current[tag]

    return hierarchy


def flatten_hierarchy(
    hierarchy: dict, prefix: str = "", max_depth: int = None, current_depth: int = 0
) -> dict:
    """
    Flatten nested hierarchy for pie chart display.

    Args:
        hierarchy: Nested dictionary structure
        prefix: Prefix for current level
        max_depth: Maximum depth to flatten (None for all)
        current_depth: Current depth in recursion

    Returns:
        Dictionary with keys as tag paths and values as durations
    """
    result = {}

    if max_depth is not None and current_depth >= max_depth:
        # Reached max depth, sum all nested values
        total = sum(
            v
            if isinstance(v, (int, float))
            else flatten_hierarchy(v, prefix, None, current_depth + 1).get("_total", 0)
            for v in hierarchy.values()
            if v != "_total"
        )
        if total > 0:
            result[prefix or "All"] = total
        return result

    for key, value in hierarchy.items():
        if key == "_total":
            continue

        new_prefix = f"{prefix} > {key}" if prefix else key

        if isinstance(value, dict):
            if "_total" in value and len(value) == 1:
                # Leaf node with only _total
                result[new_prefix] = value["_total"]
            else:
                # Has children, recurse
                nested = flatten_hierarchy(
                    value, new_prefix, max_depth, current_depth + 1
                )
                result.update(nested)
        else:
            result[new_prefix] = value

    return result


def create_sunburst_data(
    hierarchy: dict, max_depth: int
) -> Tuple[List[str], List[str], List[str], List[float]]:
    """
    Create data for sunburst chart from hierarchy.

    Returns:
        (ids, labels, parents, values)
    """
    ids = []
    labels = []
    parents = []
    values = []

    def calculate_node_value(node: dict) -> float:
        """Calculate the total value for a node (sum of all children or direct value)."""
        # Check if this is a leaf node (only has _total)
        children_keys = [k for k in node.keys() if k != "_total"]
        if not children_keys:
            # Leaf node - return its direct value
            return node.get("_total", 0)

        # Intermediate node - sum all children
        total = 0
        for key in children_keys:
            value = node[key]
            if isinstance(value, dict):
                total += calculate_node_value(value)
            else:
                total += value

        return total

    def traverse(node: dict, parent_id: str = "", depth: int = 0):
        if depth > max_depth:
            return

        for tag, data in node.items():
            if tag == "_total":
                continue

            # Create unique ID for this node
            if parent_id:
                current_id = f"{parent_id} > {tag}"
            else:
                current_id = tag

            if isinstance(data, dict):
                # Check if this node has children (besides _total)
                has_children = any(k != "_total" for k in data.keys())

                # Calculate the value for this node
                node_value = calculate_node_value(data)

                if node_value > 0:
                    ids.append(current_id)
                    labels.append(tag)
                    parents.append(parent_id if parent_id else "")
                    values.append(node_value)

                # Recurse for children
                if has_children and depth < max_depth:
                    traverse(data, current_id, depth + 1)
            else:
                # Leaf value
                if data > 0:
                    ids.append(current_id)
                    labels.append(tag)
                    parents.append(parent_id if parent_id else "")
                    values.append(data)

    traverse(hierarchy, "", 0)
    return ids, labels, parents, values


@st.cache_data
def load_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Load and cache data from database."""
    with TimetaggerDB() as db:
        records = db.get_parsed_records(start_date, end_date)
    return pd.DataFrame(records)


def main():
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # Check authentication
    if not st.session_state["authenticated"]:
        st.set_page_config(page_title="Timetagger Analytics - Login", layout="centered")
        show_login_page()
        return

    st.set_page_config(page_title="Timetagger Analytics", layout="wide")

    # Logout button in sidebar
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.get('username', 'User')}**")
        if st.button("Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.rerun()

    st.title("📊 Timetagger Analytics")

    # Initialize database connection
    try:
        with TimetaggerDB() as db:
            # Get date range from all records
            all_records = db.get_parsed_records()
            if not all_records:
                st.error("No records found in database.")
                return

            min_date = min(
                r["datetime_start"] for r in all_records if r["datetime_start"]
            )
            max_date = max(r["datetime_end"] for r in all_records if r["datetime_end"])
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return

    # Sidebar controls
    st.sidebar.header("Filters")

    # Date range selector
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=min_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=max_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )

    if start_date > end_date:
        st.sidebar.error("Start date must be before end date.")
        return

    # Convert to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Load data
    df = load_data(start_datetime, end_datetime)

    if df.empty:
        st.warning("No records found for selected date range.")
        return

    # Display summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        total_duration = df["duration"].sum()
        hours = total_duration / 3600
        st.metric("Total Time", f"{hours:.1f} hours")
    with col3:
        avg_duration = df["duration"].mean()
        st.metric("Avg Duration", f"{avg_duration / 60:.1f} min")
    with col4:
        unique_tags = set()
        for tags in df["tags"]:
            unique_tags.update(tags)
        st.metric("Unique Tags", len(unique_tags))

    st.divider()

    # Sunburst chart section
    st.header("📈 Multi-level Sunburst Chart by Tags")

    # Depth selector for sunburst chart
    max_tag_depth = st.slider(
        "Tag Hierarchy Depth", min_value=1, max_value=5, value=2, key="sunburst_depth"
    )

    # Group records by tags
    records_list = df.to_dict("records")
    hierarchy = group_by_tags_hierarchy(records_list, max_tag_depth)

    # Create sunburst chart
    if hierarchy:
        # Create sunburst data
        ids, labels, parents, values = create_sunburst_data(hierarchy, max_tag_depth)

        if ids and values:
            # Convert values to hours for better readability
            values_hours = [v / 3600 for v in values]

            # Create sunburst chart
            fig_sunburst = go.Figure(
                go.Sunburst(
                    ids=ids,
                    labels=labels,
                    parents=parents,
                    values=values_hours,
                    branchvalues="total",  # Values represent totals including all descendants
                    hovertemplate="<b>%{label}</b><br>Duration: %{value:.2f} hours<br>%{percentParent:.1%} of parent<extra></extra>",
                    maxdepth=max_tag_depth,
                )
            )
            fig_sunburst.update_layout(
                title=f"Time Distribution by Tags (Depth: {max_tag_depth})",
                height=700,
                margin=dict(t=50, l=0, r=0, b=0),
            )
            st.plotly_chart(fig_sunburst, width="stretch")
        else:
            st.info("No data to display for selected depth.")
    else:
        st.info("No records with tags found.")

    st.divider()

    # Stacked bar chart section
    st.header("📊 Stacked Bar Chart by Time Period and Level 1 Tags")

    # Granularity selector for bar chart
    granularity = st.selectbox(
        "Granularity", ["days", "weeks", "months"], index=1, key="bar_granularity"
    )

    # Group records by period and level 1 tags
    period_tag_data = group_by_period_and_tags(records_list, granularity)

    if period_tag_data:
        # Get all unique tags across all periods
        all_tags = set()
        for period_data in period_tag_data.values():
            all_tags.update(period_data.keys())
        all_tags = sorted(all_tags)

        # Get sorted period keys
        sorted_periods = sorted(period_tag_data.keys())

        # Prepare data for stacked bar chart
        # Each tag will be a separate trace
        fig_bar = go.Figure()

        # Create a trace for each tag
        for tag in all_tags:
            values = []
            for period in sorted_periods:
                values.append(
                    period_tag_data[period].get(tag, 0) / 3600
                )  # Convert to hours

            fig_bar.add_trace(
                go.Bar(
                    name=tag,
                    x=sorted_periods,
                    y=values,
                    hovertemplate=f"<b>{tag}</b><br>Period: %{{x}}<br>Duration: %{{y:.2f}} hours<extra></extra>",
                )
            )

        # Format period labels for display
        if granularity == "days":
            x_labels = [
                datetime.strptime(p, "%Y-%m-%d").strftime("%b %d, %Y")
                for p in sorted_periods
            ]
        elif granularity == "weeks":
            x_labels = [
                f"Week {p.split('-W')[1]}, {p.split('-W')[0]}" for p in sorted_periods
            ]
        elif granularity == "months":
            x_labels = [
                datetime.strptime(p, "%Y-%m").strftime("%B %Y") for p in sorted_periods
            ]
        else:
            x_labels = sorted_periods

        fig_bar.update_layout(
            title=f"Time Distribution by {granularity.capitalize()} and Level 1 Tags",
            xaxis_title="Time Period",
            yaxis_title="Hours",
            barmode="stack",  # Stacked bars
            height=500,
            xaxis={
                "tickmode": "array",
                "tickvals": sorted_periods,
                "ticktext": x_labels,
                "tickangle": -45,
            },
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
            ),
        )
        st.plotly_chart(fig_bar, width="stretch")

        # Display table
        with st.expander("View Data Table"):
            # Create a table with periods as rows and tags as columns
            table_data = []
            for period in sorted_periods:
                row = {"Period": period}
                for tag in all_tags:
                    row[tag] = period_tag_data[period].get(tag, 0) / 3600
                table_data.append(row)

            table_df = pd.DataFrame(table_data)
            st.dataframe(table_df, width="stretch")
    else:
        st.info("No data to display.")


if __name__ == "__main__":
    main()
