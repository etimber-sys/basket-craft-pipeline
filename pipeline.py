from extract import extract
from transform import transform


def main():
    """Run the full ELT pipeline: extract from MySQL, then transform in PostgreSQL."""
    print("Extracting from MySQL into staging tables...")
    extract()
    print("Transforming staging tables into monthly_sales...")
    transform()
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
