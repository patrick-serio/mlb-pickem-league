import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, AnchorFlowable
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import re

# =========================
# FONTS (in assets/fonts/)
# =========================

pdfmetrics.registerFont(TTFont("Nexa", "assets/fonts/Nexa-Heavy.ttf"))
pdfmetrics.registerFont(TTFont("Lobster", "assets/fonts/Lobster-Regular.ttf"))

# =========================
# HELPERS
# =========================

def sanitize_anchor_name(name):
    return re.sub(r'[^A-Za-z0-9_]', '', name.replace(' ', '_'))

def hex_to_color(hex_code):
    hex_code = hex_code.lstrip("#")
    return colors.Color(
        int(hex_code[0:2], 16) / 255.0,
        int(hex_code[2:4], 16) / 255.0,
        int(hex_code[4:6], 16) / 255.0
    )

def draw_background(canvas, doc):
    canvas.setFillColor(hex_to_color("#D5A451"))
    canvas.rect(0, 0, letter[0], letter[1], fill=True, stroke=False)

def draw_cover(canvas, doc, cover_page_path):
    canvas.drawImage(cover_page_path, 0, 0, width=letter[0], height=letter[1])
    canvas.showPage()
    draw_background(canvas, doc)

# =========================
# DATA CLEANING
# =========================

def clean_data(df):
    df["Team"] = df["Team"].ffill()
    df["Total Score"] = pd.to_numeric(df["Total Score"], errors="coerce").fillna(0)
    return df

# =========================
# PDF GENERATION
# =========================

def generate_pdf_summary(df, cover_page_path, output_filename="output/fantasy_summary.pdf"):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)

    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    styles["Title"].fontName = "Nexa"
    styles["Heading3"].fontName = "Nexa"
    styles["Normal"].fontName = "Nexa"

    team_totals = (
        df.groupby("Team")["Total Score"]
        .sum()
        .reset_index()
        .sort_values(by="Total Score", ascending=False)
    )

    # Colors
    header_color = hex_to_color("#303444")
    text_color = hex_to_color("#FFFFFF")
    background_color = hex_to_color("#D5C69E")
    grid_color = hex_to_color("#303444")
    injured_color = hex_to_color("#D14B36")

    # =========================
    # LEADERBOARD ANCHOR
    # =========================
    elements.append(AnchorFlowable("Leaderboard"))
    elements.append(
        Paragraph(
            '<font color="#303444">League Leaderboard</font>',
            styles["Title"]
        )
    )
    elements.append(Spacer(1, 12))

    leaderboard_data = [["Rank", "Team", "Total Points"]]

    for rank, (_, row) in enumerate(team_totals.iterrows(), start=1):
        team_name = row["Team"]

        # clickable link to team section
        team_link = Paragraph(
            f'<font color="#d14b36"><u><a href="#{sanitize_anchor_name(team_name)}">{team_name}</a></u></font>',
            styles["Normal"]
)

        leaderboard_data.append([
            rank,
            team_link,
            int(row["Total Score"])
        ])

    leaderboard_table = Table(leaderboard_data, colWidths=[50, 200, 100])
    leaderboard_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), text_color),
        ("TEXTCOLOR", (0, 1), (-1, -1), hex_to_color("#303444")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Nexa"),
        ("BACKGROUND", (0, 1), (-1, -1), background_color),
        ("GRID", (0, 0), (-1, -1), 1, grid_color)
    ]))

    elements.append(leaderboard_table)
    elements.append(PageBreak())

    # =========================
    # TEAM SECTIONS
    # =========================
    for owner, team_df in df.groupby("Team"):

        total_points = team_df["Total Score"].sum()

        # anchor target for leaderboard links
        elements.append(AnchorFlowable(sanitize_anchor_name(owner)))

        elements.append(
            Paragraph(
                f'<font color="#303444">{owner}\'s Team: {int(total_points)} points</font>',
                styles["Heading3"]
            )
        )

        elements.append(Spacer(1, 6))

        table_data = [["Position", "Player", "Score"]]

        table_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), text_color),
            ("TEXTCOLOR", (0, 1), (-1, -1), hex_to_color("#303444")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, -1), "Nexa"),
            ("BACKGROUND", (0, 1), (-1, -1), background_color),
            ("GRID", (0, 0), (-1, -1), 1, grid_color)
        ]

        for i, row in team_df.iterrows():
            table_data.append([
                row["Position"],
                row.get("Full Name", row["Player"]),
                int(row["Total Score"])
            ])

            # =========================
            # INJURED PLAYER HIGHLIGHT
            # =========================
            if row.get("Injured") == "Y":
                table_styles.append((
                    "BACKGROUND",
                    (0, len(table_data) - 1),
                    (-1, len(table_data) - 1),
                    injured_color
                ))

        team_table = Table(table_data, colWidths=[90, 200, 90])
        team_table.setStyle(TableStyle(table_styles))

        elements.append(team_table)

        # =========================
        # BACK TO LEADERBOARD LINK
        # =========================
        elements.append(Spacer(1, 12))

        back_link = Paragraph(
            '<para align="right"><font color="#D14B36"><u><a href="#Leaderboard">Back to Leaderboard</a></u></font></para>',
            styles["Normal"]
)

        elements.append(back_link)
        elements.append(PageBreak())

    # =========================
    # BUILD PDF
    # =========================
    doc.build(
        elements,
        onFirstPage=lambda c, d: draw_cover(c, d, cover_page_path),
        onLaterPages=draw_background
    )

    print(f"PDF generated → {output_filename}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    file_path = "data/team_rosters_updated.csv"
    cover_page_path = "assets/Cover_Page_2026.png"

    df = pd.read_csv(file_path)
    df = clean_data(df)

    generate_pdf_summary(df, cover_page_path)
