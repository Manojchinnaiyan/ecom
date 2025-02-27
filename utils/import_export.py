# 5. Import/Export System
# utils/import_export.py
import csv
import pandas as pd
from io import StringIO, BytesIO
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows


class ImportExportService:
    """
    Service for importing and exporting data.
    """

    @staticmethod
    def export_products(queryset, format="csv"):
        """
        Export products to CSV or Excel.
        """
        # Prepare data for export
        data = []
        for product in queryset:
            # Get primary image URL if it exists
            primary_image = product.images.filter(is_primary=True).first()
            image_url = primary_image.image.url if primary_image else ""

            # Get categories as comma-separated string
            categories = ", ".join([cat.name for cat in product.categories.all()])

            # Add product data
            product_data = {
                "ID": str(product.id),
                "SKU": product.sku,
                "Name": product.name,
                "Description": product.description,
                "Price": product.price,
                "Compare At Price": product.compare_at_price or "",
                "Cost Price": product.cost_price or "",
                "Stock Quantity": product.stock_quantity,
                "Categories": categories,
                "Is Active": product.is_active,
                "Is Featured": product.is_featured,
                "Is Digital": product.is_digital,
                "Meta Title": product.meta_title or "",
                "Meta Description": product.meta_description or "",
                "Image URL": image_url,
                "Created At": product.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            data.append(product_data)

        # Create DataFrame for easier manipulation
        df = pd.DataFrame(data)

        if format == "csv":
            # Export to CSV
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)

            response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="products_export.csv"'
            )
            return response

        elif format == "excel":
            # Export to Excel
            excel_buffer = BytesIO()

            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Products"

            # Add header row
            for row in dataframe_to_rows(df, index=False, header=True):
                ws.append(row)

            # Save to buffer
            wb.save(excel_buffer)
            excel_buffer.seek(0)

            response = HttpResponse(
                excel_buffer.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                'attachment; filename="products_export.xlsx"'
            )
            return response

        else:
            raise ValueError(f"Unsupported export format: {format}")

    @staticmethod
    def import_products(file_obj, file_format="csv"):
        """
        Import products from CSV or Excel.
        """
        results = {"created": 0, "updated": 0, "errors": []}

        try:
            # Read data based on format
            if file_format == "csv":
                df = pd.read_csv(file_obj)
            elif file_format == "excel":
                df = pd.read_excel(file_obj)
            else:
                raise ValueError(f"Unsupported import format: {file_format}")

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Check if product exists (by SKU or ID)
                    product = None
                    if "SKU" in row and row["SKU"]:
                        try:
                            product = Product.objects.get(sku=row["SKU"])
                        except Product.DoesNotExist:
                            pass

                    if not product and "ID" in row and row["ID"]:
                        try:
                            product = Product.objects.get(id=row["ID"])
                        except (Product.DoesNotExist, ValidationError):
                            pass

                    # Prepare product data
                    product_data = {
                        "name": row.get("Name", ""),
                        "sku": row.get("SKU", ""),
                        "description": row.get("Description", ""),
                        "price": row.get("Price", 0),
                        "is_active": row.get("Is Active", True),
                    }

                    # Add optional fields if present
                    if "Compare At Price" in row and pd.notna(row["Compare At Price"]):
                        product_data["compare_at_price"] = row["Compare At Price"]

                    if "Cost Price" in row and pd.notna(row["Cost Price"]):
                        product_data["cost_price"] = row["Cost Price"]

                    if "Stock Quantity" in row and pd.notna(row["Stock Quantity"]):
                        product_data["stock_quantity"] = int(row["Stock Quantity"])

                    if "Is Featured" in row and pd.notna(row["Is Featured"]):
                        product_data["is_featured"] = row["Is Featured"]

                    if "Is Digital" in row and pd.notna(row["Is Digital"]):
                        product_data["is_digital"] = row["Is Digital"]

                    if "Meta Title" in row and pd.notna(row["Meta Title"]):
                        product_data["meta_title"] = row["Meta Title"]

                    if "Meta Description" in row and pd.notna(row["Meta Description"]):
                        product_data["meta_description"] = row["Meta Description"]

                    # Create or update product
                    if product:
                        # Update existing product
                        for key, value in product_data.items():
                            setattr(product, key, value)
                        product.save()
                        results["updated"] += 1
                    else:
                        # Create new product
                        product = Product.objects.create(**product_data)
                        results["created"] += 1

                    # Handle categories if present
                    if "Categories" in row and pd.notna(row["Categories"]):
                        categories = row["Categories"].split(",")
                        for category_name in categories:
                            category_name = category_name.strip()
                            if category_name:
                                # Get or create category
                                try:
                                    category = Category.objects.get(name=category_name)
                                except Category.DoesNotExist:
                                    # Create slug from name
                                    from django.utils.text import slugify

                                    slug = slugify(category_name)
                                    category = Category.objects.create(
                                        name=category_name, slug=slug
                                    )

                                # Add category to product
                                product.categories.add(category)

                    # Handle image if URL is provided and product is new
                    if (
                        "Image URL" in row
                        and pd.notna(row["Image URL"])
                        and not product.images.exists()
                    ):
                        # This would need external image import functionality
                        # and handling remote file downloads which is complex
                        # For now, log this as a note
                        pass

                except Exception as e:
                    # Log the error and continue with next row
                    results["errors"].append(f"Error at row {index + 2}: {str(e)}")

            return results

        except Exception as e:
            # Handle file-level errors
            results["errors"].append(f"File import error: {str(e)}")
            return results
