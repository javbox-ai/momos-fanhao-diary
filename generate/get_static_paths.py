def get_static_paths(base_url):
    # Ensure base_url ends with a slash
    if not base_url.endswith('/'):
        base_url += '/'
    
    # Define your static asset paths here
    # These are examples, adjust them to your project structure
    return {
        "css_main_url": f"{base_url}static/css/main.css",
        "js_main_url": f"{base_url}static/js/main.js",
        "logo_url": f"{base_url}static/images/logo.png",
        "placeholder_image_url": f"{base_url}static/images/placeholder.jpg",
        "cover_image_example_url": f"{base_url}static/images/covers/example_cover.jpg", # Example for covers
        # Add more paths as needed, e.g., for specific CSS/JS files per page, fonts, etc.
        # "css_page_specific_url": f"{base_url}static/css/page_specific.css",
        # "font_awesome_url": f"{base_url}static/vendor/fontawesome/css/all.min.css",
    }

if __name__ == '__main__':
    # Example usage (optional, for testing this module directly)
    test_base_url = "http://localhost:8000"
    paths = get_static_paths(test_base_url)
    print("Generated static paths:")
    for key, value in paths.items():
        print(f"  {key}: {value}")

    test_base_url_with_slash = "https://example.com/"
    paths_with_slash = get_static_paths(test_base_url_with_slash)
    print("\nGenerated static paths (URL with trailing slash):")
    for key, value in paths_with_slash.items():
        print(f"  {key}: {value}") 