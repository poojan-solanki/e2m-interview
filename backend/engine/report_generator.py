"""Report Generator for Contractor-Ready Bill of Quantities.

Generates ASCII tables for terminal/CLI output, structured JSON for API responses,
and professional printable HTML reports for contractor discussions.
"""

import json
from datetime import datetime
from typing import Optional
from .boq_calculator import BoQSummary


def generate_ascii_report(
    summary: BoQSummary,
    project_title: str = "Exterior House Renovation Estimate",
    client_name: str = "Homeowner",
) -> str:
    """Generates a clean terminal/console formatted ASCII table."""
    lines = []
    separator = "-" * 88
    double_sep = "=" * 88

    lines.append(double_sep)
    lines.append(f"  AI EXTERIOR RENOVATION & COST ESTIMATION REPORT")
    lines.append(f"  Project: {project_title} | Client: {client_name} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(double_sep)

    header = f"{'Zone / Location':<22} | {'Material Applied':<24} | {'Net Area':<10} | {'Mat. Cost':<12} | {'Labor Cost':<11} | {'Line Total':<11}"
    lines.append(header)
    lines.append(separator)

    for item in summary.items:
        net_str = f"{item.net_workable_area:.1f} {item.unit}"
        mat_cost = f"Rs.{item.material_cost_inr:,.0f}"
        lab_cost = f"Rs.{item.labor_cost_inr:,.0f}"
        line_total = f"Rs.{item.line_total_inr:,.0f}"
        lines.append(
            f"{item.zone_name[:22]:<22} | {item.material_name[:24]:<24} | {net_str:<10} | {mat_cost:<12} | {lab_cost:<11} | {line_total:<11}"
        )
        # Add secondary line detailing consumption & wastage
        lines.append(
            f"  [+] Gross: {item.gross_surface_area:.1f} {item.unit} | Openings: -{item.deductions_area:.1f} | Wastage: +{item.wastage_percentage}% | Qty: {item.gross_consumption_qty:.1f} {item.consumption_unit}"
        )

    lines.append(separator)
    lines.append(f"{'CATEGORY BREAKDOWN:':<48} | {'FINANCIAL TOTALS:':<37}")
    
    # Pair category totals with summary totals
    cat_items = list(summary.category_totals_inr.items())
    fin_lines = [
        f"Material Subtotal : Rs.{summary.total_material_cost_inr:,.2f}",
        f"Labor Subtotal    : Rs.{summary.total_labor_cost_inr:,.2f}",
        f"Subtotal          : Rs.{summary.subtotal_inr:,.2f}",
        f"Contingency ({summary.contingency_percentage:.0f}%): Rs.{summary.contingency_amount_inr:,.2f}",
    ]

    max_rows = max(len(cat_items), len(fin_lines))
    for i in range(max_rows):
        cat_str = f"* {cat_items[i][0].capitalize():<14} : Rs.{cat_items[i][1]:,.0f}" if i < len(cat_items) else ""
        fin_str = fin_lines[i] if i < len(fin_lines) else ""
        lines.append(f"{cat_str:<48} | {fin_str:<37}")

    lines.append(double_sep)
    lines.append(f"  GRAND TOTAL ESTIMATE (INR): Rs.{summary.grand_total_inr:,.2f}")
    lines.append(double_sep)
    lines.append("  Note: Advisory estimate for pre-construction planning. Rates based on Ahmedabad region.")
    lines.append("")

    return "\n".join(lines)


def generate_html_report(
    summary: BoQSummary,
    project_title: str = "Exterior Renovation Takeoff & Cost Estimate",
    client_name: str = "Valued Homeowner",
    original_image_path: Optional[str] = None,
    redesigned_image_path: Optional[str] = None,
) -> str:
    """Generates a professional, self-contained contractor discussion report in HTML."""
    date_str = datetime.now().strftime("%B %d, %Y")

    # Build table rows
    rows_html = []
    for item in summary.items:
        rows_html.append(f"""
        <tr>
            <td>
                <strong>{item.zone_name}</strong><br/>
                <small style="color: #64748b;">ID: {item.zone_id}</small>
            </td>
            <td>
                <strong>{item.material_name}</strong><br/>
                <span class="badge badge-category">{item.category.upper()}</span>
            </td>
            <td>
                {item.gross_surface_area:.1f} {item.unit}
                {f'<br/><small style="color: #ef4444;">-{item.deductions_area:.1f} openings</small>' if item.deductions_area > 0 else ''}
            </td>
            <td>
                <strong>{item.net_workable_area:.1f} {item.unit}</strong><br/>
                <small style="color: #059669;">+{item.wastage_percentage}% waste</small>
            </td>
            <td>
                <strong>{item.gross_consumption_qty:,.1f} {item.consumption_unit}</strong>
            </td>
            <td>₹{item.unit_material_rate_inr:,.0f} / ₹{item.unit_labor_rate_inr:,.0f}</td>
            <td style="text-align: right; font-weight: 600;">₹{item.line_total_inr:,.2f}</td>
        </tr>
        """)
    table_body = "\n".join(rows_html)

    # Build category breakdown tags
    cat_html = []
    for cat, amount in summary.category_totals_inr.items():
        cat_html.append(f"""
        <div class="summary-card">
            <span class="card-label">{cat.upper()}</span>
            <span class="card-value">₹{amount:,.0f}</span>
        </div>
        """)
    categories_rendered = "\n".join(cat_html)

    # Optional image section
    image_section = ""
    if original_image_path or redesigned_image_path:
        orig_img = f'<img src="{original_image_path}" alt="Original Facade"/>' if original_image_path else '<div class="no-img">Original Photo</div>'
        rend_img = f'<img src="{redesigned_image_path}" alt="Redesigned Facade"/>' if redesigned_image_path else '<div class="no-img">AI Redesign Render</div>'
        image_section = f"""
        <div class="image-comparison">
            <div class="img-box">
                <h4>Original Facade</h4>
                {orig_img}
            </div>
            <div class="img-box">
                <h4>Proposed AI Redesign</h4>
                {rend_img}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{project_title} - Contractor BoQ Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; }}
        body {{ background: #f8fafc; color: #0f172a; padding: 32px; font-size: 14px; line-height: 1.5; }}
        .container {{ max-width: 1040px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); padding: 40px; }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #e2e8f0; padding-bottom: 24px; margin-bottom: 28px; }}
        .brand h1 {{ font-size: 24px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }}
        .brand p {{ color: #64748b; font-size: 13px; }}
        .meta-box {{ text-align: right; font-size: 13px; color: #475569; }}
        .meta-box strong {{ color: #0f172a; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
        .badge-category {{ background: #e0f2fe; color: #0369a1; }}
        .image-comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }}
        .img-box {{ background: #f1f5f9; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1; text-align: center; }}
        .img-box h4 {{ padding: 10px; background: #e2e8f0; font-size: 12px; text-transform: uppercase; color: #475569; }}
        .img-box img {{ width: 100%; max-height: 320px; object-fit: cover; display: block; }}
        .no-img {{ padding: 80px 20px; color: #94a3b8; font-style: italic; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 28px; }}
        th {{ background: #f8fafc; color: #475569; font-weight: 600; text-align: left; padding: 12px; border-bottom: 2px solid #cbd5e1; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 14px 12px; border-bottom: 1px solid #e2e8f0; }}
        .categories-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 28px; }}
        .summary-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; text-align: center; }}
        .card-label {{ display: block; font-size: 11px; color: #64748b; font-weight: 600; }}
        .card-value {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 4px; display: block; }}
        .totals-section {{ display: flex; justify-content: flex-end; margin-bottom: 32px; }}
        .totals-table {{ width: 360px; }}
        .totals-table td {{ padding: 8px 12px; }}
        .grand-total {{ background: #1e293b; color: #ffffff; border-radius: 6px; font-size: 16px; font-weight: 700; }}
        .grand-total td {{ color: #ffffff; padding: 12px; }}
        .disclaimer {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 4px; font-size: 12px; color: #92400e; }}
        @media print {{
            body {{ padding: 0; background: #ffffff; }}
            .container {{ box-shadow: none; padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">
                <h1>AI Exterior House Renovation</h1>
                <p>Detailed Pre-Construction Takeoff & Bill of Quantities (BoQ)</p>
            </div>
            <div class="meta-box">
                <p>Project: <strong>{project_title}</strong></p>
                <p>Client: <strong>{client_name}</strong></p>
                <p>Date: <strong>{date_str}</strong></p>
                <p>Currency: <strong>INR (₹)</strong></p>
            </div>
        </div>

        {image_section}

        <h3 style="margin-bottom: 12px; color: #1e293b;">Category Subtotals</h3>
        <div class="categories-grid">
            {categories_rendered}
        </div>

        <h3 style="margin-bottom: 12px; color: #1e293b;">Itemized Bill of Quantities</h3>
        <table>
            <thead>
                <tr>
                    <th>Zone</th>
                    <th>Material</th>
                    <th>Gross Area</th>
                    <th>Net Workable</th>
                    <th>Material Qty</th>
                    <th>Unit Rates (Mat/Lab)</th>
                    <th style="text-align: right;">Line Total</th>
                </tr>
            </thead>
            <tbody>
                {table_body}
            </tbody>
        </table>

        <div class="totals-section">
            <table class="totals-table">
                <tr>
                    <td>Total Material Cost:</td>
                    <td style="text-align: right; font-weight: 600;">₹{summary.total_material_cost_inr:,.2f}</td>
                </tr>
                <tr>
                    <td>Total Labor Cost:</td>
                    <td style="text-align: right; font-weight: 600;">₹{summary.total_labor_cost_inr:,.2f}</td>
                </tr>
                <tr>
                    <td>Subtotal:</td>
                    <td style="text-align: right; font-weight: 600;">₹{summary.subtotal_inr:,.2f}</td>
                </tr>
                <tr>
                    <td>Contingency ({summary.contingency_percentage:.0f}%):</td>
                    <td style="text-align: right; font-weight: 600;">₹{summary.contingency_amount_inr:,.2f}</td>
                </tr>
                <tr class="grand-total">
                    <td>GRAND TOTAL:</td>
                    <td style="text-align: right;">₹{summary.grand_total_inr:,.2f}</td>
                </tr>
            </table>
        </div>

        <div class="disclaimer">
            <strong>Advisory Notice:</strong> This cost estimate is generated based on optical surface area calculations and standard regional construction rates (Ahmedabad / Gujarat market). Quantities include standard civil cutting and spill allowances (5% to 15%). Final quotation should be verified by a licensed contractor after on-site physical inspection.
        </div>
    </div>
</body>
</html>
"""
    return html


def generate_json_report(summary: BoQSummary) -> str:
    """Serializes the BoQ calculation to a clean JSON string."""
    return json.dumps(summary.to_dict(), indent=2)
