from docs_for_me.core.structure import summarize_structure


def test_summarize_python_structure() -> None:
    content = "import os\n\nclass Runner:\n    pass\n\ndef main():\n    pass\n"

    result = summarize_structure(content, "Python")

    assert "import: `import os`" in result
    assert "class: `Runner`" in result
    assert "function: `main`" in result


def test_summarize_typescript_react_structure() -> None:
    content = (
        "import Link from 'next/link'\n\n"
        "interface PageProps {\n"
        "  id: string\n"
        "}\n\n"
        "export default function BookingsPage() {\n"
        "  return <main />\n"
        "}\n"
    )

    result = summarize_structure(content, "TypeScript React")

    assert "import: `import Link from 'next/link'`" in result
    assert "interface: `PageProps`" in result
    assert "function: `BookingsPage`" in result
