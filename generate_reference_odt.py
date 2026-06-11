#!/usr/bin/env python3
"""Generate a reference.odt matching the eisvogel PDF template style.

Eisvogel uses:
  - Accent color: #7137C8 (purple)
  - Title page with logo, title, author, date
  - Clean sans-serif headings
  - Monospace code blocks with light background

This script creates a minimal ODF document whose automatic and common
styles mirror that look.  Pandoc's --reference-doc will inherit these
styles when producing .odt output.
"""

import zipfile, io, os, textwrap

ACCENT = "#7137C8"
ACCENT_LIGHT = "#f0e6fc"  # light purple tint for code bg
FONT_HEADING = "Liberation Sans"
FONT_BODY = "Liberation Serif"
FONT_MONO = "Liberation Mono"

# ── ODF boilerplate ──────────────────────────────────────────────────────────

MIMETYPE = "application/vnd.oasis.opendocument.text"

MANIFEST = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
                   manifest:version="1.2">
  <manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.text"
                       manifest:full-path="/"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="styles.xml"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="meta.xml"/>
</manifest:manifest>
""")

META = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
    office:version="1.2">
  <office:meta>
    <meta:generator>generate_reference_odt.py</meta:generator>
  </office:meta>
</office:document-meta>
""")

# ── styles.xml — this is the heart of the reference document ─────────────────

STYLES = textwrap.dedent(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
    xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    office:version="1.2">

  <!-- ── Font declarations ────────────────────────────────────── -->
  <office:font-face-decls>
    <style:font-face style:name="{FONT_HEADING}"
        svg:font-family="'{FONT_HEADING}'" style:font-family-generic="swiss"/>
    <style:font-face style:name="{FONT_BODY}"
        svg:font-family="'{FONT_BODY}'" style:font-family-generic="roman"/>
    <style:font-face style:name="{FONT_MONO}"
        svg:font-family="'{FONT_MONO}'" style:font-family-generic="modern"
        style:font-pitch="fixed"/>
  </office:font-face-decls>

  <!-- ── Default styles (base for everything) ─────────────────── -->
  <office:styles>

    <!-- Default paragraph properties -->
    <style:default-style style:family="paragraph">
      <style:paragraph-properties
          fo:margin-top="0cm" fo:margin-bottom="0.25cm"
          fo:line-height="150%" fo:text-align="start"
          fo:orphans="2" fo:widows="2"/>
      <style:text-properties
          style:font-name="{FONT_BODY}" fo:font-size="11pt"
          fo:color="#333333" fo:language="sv" fo:country="SE"/>
    </style:default-style>

    <!-- Default table properties -->
    <style:default-style style:family="table">
      <style:table-properties table:border-model="collapsing"/>
    </style:default-style>

    <!-- ── Named paragraph styles ─────────────────────────────── -->

    <!-- Body Text / Default -->
    <style:style style:name="Standard" style:family="paragraph"
                 style:class="text">
      <style:paragraph-properties fo:margin-bottom="0.25cm"
          fo:line-height="150%"/>
      <style:text-properties style:font-name="{FONT_BODY}"
          fo:font-size="11pt" fo:color="#333333"/>
    </style:style>

    <!-- Text Body (used by pandoc for normal paragraphs) -->
    <style:style style:name="Text_20_Body" style:display-name="Text Body"
                 style:family="paragraph" style:parent-style-name="Standard"
                 style:class="text">
      <style:paragraph-properties fo:margin-bottom="0.25cm"
          fo:line-height="150%"/>
    </style:style>

    <!-- First line indent -->
    <style:style style:name="First_20_line_20_indent"
                 style:display-name="First line indent"
                 style:family="paragraph"
                 style:parent-style-name="Text_20_Body"
                 style:class="text">
      <style:paragraph-properties fo:text-indent="0cm"/>
    </style:style>

    <!-- Title -->
    <style:style style:name="Title" style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body" style:class="chapter">
      <style:paragraph-properties fo:margin-top="0cm"
          fo:margin-bottom="0.5cm" fo:text-align="start"
          fo:break-before="page"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="28pt" fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Subtitle -->
    <style:style style:name="Subtitle" style:family="paragraph"
                 style:parent-style-name="Title"
                 style:next-style-name="Text_20_Body" style:class="chapter">
      <style:paragraph-properties fo:margin-bottom="0.8cm"/>
      <style:text-properties fo:font-size="16pt" fo:font-weight="normal"
          fo:color="#666666"/>
    </style:style>

    <!-- Author -->
    <style:style style:name="Author" style:family="paragraph"
                 style:parent-style-name="Subtitle" style:class="chapter">
      <style:text-properties fo:font-size="14pt" fo:color="#555555"/>
    </style:style>

    <!-- Date -->
    <style:style style:name="Date" style:family="paragraph"
                 style:parent-style-name="Subtitle" style:class="chapter">
      <style:text-properties fo:font-size="12pt" fo:color="#777777"/>
    </style:style>

    <!-- Heading 1 -->
    <style:style style:name="Heading_20_1" style:display-name="Heading 1"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="1" style:class="text">
      <style:paragraph-properties fo:margin-top="0.8cm"
          fo:margin-bottom="0.4cm" fo:keep-with-next="always"
          fo:border-bottom="0.5pt solid {ACCENT}"
          fo:padding-bottom="0.15cm"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="22pt" fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Heading 2 -->
    <style:style style:name="Heading_20_2" style:display-name="Heading 2"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="2" style:class="text">
      <style:paragraph-properties fo:margin-top="0.6cm"
          fo:margin-bottom="0.3cm" fo:keep-with-next="always"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="18pt" fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Heading 3 -->
    <style:style style:name="Heading_20_3" style:display-name="Heading 3"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="3" style:class="text">
      <style:paragraph-properties fo:margin-top="0.5cm"
          fo:margin-bottom="0.25cm" fo:keep-with-next="always"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="14pt" fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Heading 4 -->
    <style:style style:name="Heading_20_4" style:display-name="Heading 4"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="4" style:class="text">
      <style:paragraph-properties fo:margin-top="0.4cm"
          fo:margin-bottom="0.2cm" fo:keep-with-next="always"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="12pt" fo:font-weight="bold" fo:font-style="italic"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Heading 5 -->
    <style:style style:name="Heading_20_5" style:display-name="Heading 5"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="5" style:class="text">
      <style:paragraph-properties fo:margin-top="0.3cm"
          fo:margin-bottom="0.15cm" fo:keep-with-next="always"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="11pt" fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Heading 6 -->
    <style:style style:name="Heading_20_6" style:display-name="Heading 6"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:next-style-name="Text_20_Body"
                 style:default-outline-level="6" style:class="text">
      <style:paragraph-properties fo:margin-top="0.3cm"
          fo:margin-bottom="0.15cm" fo:keep-with-next="always"/>
      <style:text-properties style:font-name="{FONT_HEADING}"
          fo:font-size="11pt" fo:font-weight="bold" fo:font-style="italic"
          fo:color="#555555"/>
    </style:style>

    <!-- Block quote -->
    <style:style style:name="Quotations" style:family="paragraph"
                 style:parent-style-name="Standard" style:class="html">
      <style:paragraph-properties fo:margin-left="1cm"
          fo:margin-right="1cm" fo:margin-top="0.2cm"
          fo:margin-bottom="0.2cm"
          fo:border-left="3pt solid {ACCENT}"
          fo:padding-left="0.4cm"/>
      <style:text-properties fo:font-style="italic"
          fo:color="#555555"/>
    </style:style>

    <!-- Preformatted / code block -->
    <style:style style:name="Preformatted_20_Text"
                 style:display-name="Preformatted Text"
                 style:family="paragraph"
                 style:parent-style-name="Standard" style:class="html">
      <style:paragraph-properties fo:margin-top="0.2cm"
          fo:margin-bottom="0.2cm" fo:padding="0.3cm"
          fo:background-color="{ACCENT_LIGHT}"
          fo:border="0.5pt solid #d0c4e0"/>
      <style:text-properties style:font-name="{FONT_MONO}"
          fo:font-size="9pt" fo:color="#333333"/>
    </style:style>

    <!-- Source code (used by pandoc for highlighted code) -->
    <style:style style:name="Source_20_Code"
                 style:display-name="Source Code"
                 style:family="paragraph"
                 style:parent-style-name="Preformatted_20_Text">
    </style:style>

    <!-- List styles -->
    <style:style style:name="List_20_Bullet" style:display-name="List Bullet"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:class="list">
      <style:paragraph-properties fo:margin-left="1cm"
          fo:text-indent="-0.5cm"/>
    </style:style>

    <style:style style:name="List_20_Number" style:display-name="List Number"
                 style:family="paragraph"
                 style:parent-style-name="Standard"
                 style:class="list">
      <style:paragraph-properties fo:margin-left="1cm"
          fo:text-indent="-0.5cm"/>
    </style:style>

    <!-- Definition list -->
    <style:style style:name="Definition_20_Term"
                 style:display-name="Definition Term"
                 style:family="paragraph"
                 style:parent-style-name="Standard">
      <style:text-properties fo:font-weight="bold"/>
    </style:style>

    <style:style style:name="Definition_20_Term_20_Tight"
                 style:display-name="Definition Term Tight"
                 style:family="paragraph"
                 style:parent-style-name="Definition_20_Term">
      <style:paragraph-properties fo:margin-bottom="0cm"/>
    </style:style>

    <!-- ── Character / text styles ────────────────────────────── -->

    <style:style style:name="Source_20_Text"
                 style:display-name="Source Text"
                 style:family="text">
      <style:text-properties style:font-name="{FONT_MONO}"
          fo:font-size="9pt" fo:background-color="{ACCENT_LIGHT}"
          fo:color="#333333"/>
    </style:style>

    <!-- Inline code -->
    <style:style style:name="Verbatim_20_Char"
                 style:display-name="Verbatim Char"
                 style:family="text">
      <style:text-properties style:font-name="{FONT_MONO}"
          fo:font-size="9pt" fo:background-color="{ACCENT_LIGHT}"/>
    </style:style>

    <!-- Emphasis -->
    <style:style style:name="Emphasis" style:family="text">
      <style:text-properties fo:font-style="italic"/>
    </style:style>

    <!-- Strong -->
    <style:style style:name="Strong_20_Emphasis"
                 style:display-name="Strong Emphasis"
                 style:family="text">
      <style:text-properties fo:font-weight="bold"/>
    </style:style>

    <!-- Hyperlinks -->
    <style:style style:name="Internet_20_link"
                 style:display-name="Internet link"
                 style:family="text">
      <style:text-properties fo:color="{ACCENT}"
          style:text-underline-style="solid"
          style:text-underline-color="{ACCENT}"/>
    </style:style>

    <!-- Footnote -->
    <style:style style:name="Footnote_20_Symbol"
                 style:display-name="Footnote Symbol"
                 style:family="text">
      <style:text-properties fo:font-size="8pt"
          style:text-position="super 58%"/>
    </style:style>

    <!-- Syntax highlighting character styles (pandoc names) -->
    <style:style style:name="KeywordTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#5317ac"/>
    </style:style>
    <style:style style:name="DataTypeTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#005a5f"/>
    </style:style>
    <style:style style:name="DecValTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#8b3800"/>
    </style:style>
    <style:style style:name="BaseNTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#8b3800"/>
    </style:style>
    <style:style style:name="FloatTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#8b3800"/>
    </style:style>
    <style:style style:name="ConstantTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#8b3800"/>
    </style:style>
    <style:style style:name="CharTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#2544bb"/>
    </style:style>
    <style:style style:name="SpecialCharTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#2544bb"/>
    </style:style>
    <style:style style:name="StringTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#2544bb"/>
    </style:style>
    <style:style style:name="VerbatimStringTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#2544bb"/>
    </style:style>
    <style:style style:name="SpecialStringTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#2544bb"/>
    </style:style>
    <style:style style:name="ImportTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#5317ac"/>
    </style:style>
    <style:style style:name="CommentTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-style="italic" fo:color="#505050"/>
    </style:style>
    <style:style style:name="DocumentationTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-style="italic" fo:color="#505050"/>
    </style:style>
    <style:style style:name="AnnotationTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#a0522d"/>
    </style:style>
    <style:style style:name="CommentVarTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-style="italic" fo:color="#505050"/>
    </style:style>
    <style:style style:name="OtherTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>
    <style:style style:name="FunctionTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#721045"/>
    </style:style>
    <style:style style:name="VariableTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#005a5f"/>
    </style:style>
    <style:style style:name="ControlFlowTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#5317ac"/>
    </style:style>
    <style:style style:name="OperatorTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>
    <style:style style:name="BuiltInTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>
    <style:style style:name="ExtensionTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>
    <style:style style:name="PreprocessorTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#a0522d"/>
    </style:style>
    <style:style style:name="AttributeTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#005a5f"/>
    </style:style>
    <style:style style:name="RegionMarkerTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>
    <style:style style:name="InformationTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-style="italic" fo:color="#505050"/>
    </style:style>
    <style:style style:name="WarningTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:font-style="italic"
          fo:color="#a0522d"/>
    </style:style>
    <style:style style:name="AlertTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#b60000"/>
    </style:style>
    <style:style style:name="ErrorTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:font-weight="bold" fo:color="#b60000"/>
    </style:style>
    <style:style style:name="NormalTok" style:family="text"
                 style:parent-style-name="Source_20_Text">
      <style:text-properties fo:color="#333333"/>
    </style:style>

    <!-- ── Table styles ───────────────────────────────────────── -->
    <style:style style:name="Table_20_Contents"
                 style:display-name="Table Contents"
                 style:family="paragraph"
                 style:parent-style-name="Standard">
      <style:paragraph-properties fo:margin-top="0.05cm"
          fo:margin-bottom="0.05cm"/>
      <style:text-properties fo:font-size="10pt"/>
    </style:style>

    <style:style style:name="Table_20_Heading"
                 style:display-name="Table Heading"
                 style:family="paragraph"
                 style:parent-style-name="Table_20_Contents">
      <style:paragraph-properties fo:text-align="center"/>
      <style:text-properties fo:font-weight="bold"
          fo:color="{ACCENT}"/>
    </style:style>

    <!-- Outline numbering for headings -->
    <text:outline-style style:name="Outline">
      <text:outline-level-style text:level="1" style:num-format=""/>
      <text:outline-level-style text:level="2" style:num-format=""/>
      <text:outline-level-style text:level="3" style:num-format=""/>
      <text:outline-level-style text:level="4" style:num-format=""/>
      <text:outline-level-style text:level="5" style:num-format=""/>
      <text:outline-level-style text:level="6" style:num-format=""/>
    </text:outline-style>

    <!-- List style for bullets -->
    <text:list-style style:name="List_20_1" style:display-name="List 1">
      <text:list-level-style-bullet text:level="1" text:bullet-char="•">
        <style:list-level-properties text:space-before="0.5cm"
            text:min-label-width="0.5cm"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="2" text:bullet-char="◦">
        <style:list-level-properties text:space-before="1cm"
            text:min-label-width="0.5cm"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="3" text:bullet-char="▪">
        <style:list-level-properties text:space-before="1.5cm"
            text:min-label-width="0.5cm"/>
      </text:list-level-style-bullet>
    </text:list-style>

  </office:styles>

  <!-- ── Automatic styles (page layout, header/footer) ────────── -->
  <office:automatic-styles>
    <style:page-layout style:name="pm1">
      <style:page-layout-properties
          fo:page-width="21cm" fo:page-height="29.7cm"
          fo:margin-top="2cm" fo:margin-bottom="2cm"
          fo:margin-left="2.5cm" fo:margin-right="2.5cm"
          style:writing-mode="lr-tb"/>
      <style:header-style>
        <style:header-footer-properties fo:min-height="0.5cm"
            fo:margin-bottom="0.5cm"
            fo:border-bottom="0.5pt solid {ACCENT}"
            fo:padding-bottom="0.2cm"/>
      </style:header-style>
      <style:footer-style>
        <style:header-footer-properties fo:min-height="0.5cm"
            fo:margin-top="0.5cm"
            fo:border-top="0.5pt solid #cccccc"
            fo:padding-top="0.2cm"/>
      </style:footer-style>
    </style:page-layout>
  </office:automatic-styles>

  <!-- ── Master pages ─────────────────────────────────────────── -->
  <office:master-styles>
    <style:master-page style:name="Standard" style:page-layout-name="pm1">
      <style:header>
        <text:p text:style-name="Standard">
        </text:p>
      </style:header>
      <style:footer>
        <text:p text:style-name="Standard">
          <text:page-number text:select-page="current"/>
        </text:p>
      </style:footer>
    </style:master-page>
  </office:master-styles>

</office:document-styles>
""")

# ── content.xml — minimal, pandoc replaces body content ──────────────────────

CONTENT = textwrap.dedent(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    office:version="1.2">

  <office:font-face-decls>
    <style:font-face style:name="{FONT_HEADING}"
        svg:font-family="'{FONT_HEADING}'" style:font-family-generic="swiss"/>
    <style:font-face style:name="{FONT_BODY}"
        svg:font-family="'{FONT_BODY}'" style:font-family-generic="roman"/>
    <style:font-face style:name="{FONT_MONO}"
        svg:font-family="'{FONT_MONO}'" style:font-family-generic="modern"
        style:font-pitch="fixed"/>
  </office:font-face-decls>

  <office:body>
    <office:text>
      <text:p text:style-name="Standard"/>
    </office:text>
  </office:body>

</office:document-content>
""")

# ── Build the .odt (ZIP) ─────────────────────────────────────────────────────

def build_odt(path: str) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype MUST be first and stored (not compressed)
        zf.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/manifest.xml", MANIFEST)
        zf.writestr("meta.xml", META)
        zf.writestr("styles.xml", STYLES)
        zf.writestr("content.xml", CONTENT)

    with open(path, "wb") as f:
        f.write(buf.getvalue())
    print(f"✓ Created {path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.odt")
    build_odt(out)
