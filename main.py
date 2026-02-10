"""Main entry point for the news pipeline application."""

from news_pipeline import NewsPipeline, AppConfig


def main():
    """Run the news pipeline."""
    # Create default configuration
    config = AppConfig.create_default()

    # Initialize pipeline
    pipeline = NewsPipeline(config)

    # Run pipeline with query
    results = pipeline.run("chatgpt")


if __name__ == "__main__":
    main()