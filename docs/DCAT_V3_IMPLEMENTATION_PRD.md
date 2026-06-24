# Product Requirements Document: DCAT v3 Compliance Implementation

**Version:** 1.0
**Date:** 2026-01-15
**Status:** Superseded (see status note below)
**Author:** Technical Team
**Stakeholders:** GFBio Development Team

---

> **Status note (2026-06-24):** This PRD is **superseded**. The owner-approved
> SAHIS project brief (2026-06-23) sets the forward direction as a cutover to an
> **external, `nexus`-compiled DCAT-AP catalog** — the GFBio Data Catalog at
> `catalog.gfbio.dev` — rather than building DCAT v3 inside the Aggregator. It is
> retained for historical reference and does not describe planned work on this
> codebase.

## Executive Summary

This document outlines the requirements for implementing full DCAT (Data
Catalog Vocabulary) v3 compliance in the GFBio Aggregator platform. The
implementation will transform the current simple dataset catalog into a
comprehensive, standards-compliant metadata management system that follows W3C
DCAT v3 specifications.

### Objectives

1. **Database Layer**: Design and implement a complete relational database
   schema that can store all DCAT v3 metadata elements

2. **Validation Layer**: Create comprehensive Pydantic models for data
   validation and serialization

3. **API Layer**: Develop RESTful CRUD endpoints for managing all DCAT v3
   entities

4. **Standards Compliance**: Ensure 100% compatibility with DCAT v3
   specification for future RDF export capability

### Key Deliverables

- SQLAlchemy database models with full relationship mapping
- Alembic migration scripts for database schema
- Pydantic schemas for validation and deserialization/serialization
- FastAPI CRUD endpoints for all DCAT v3 entities
- Comprehensive test suite
- Technical documentation

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [DCAT v3 Overview](#dcat-v3-overview)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Technical Architecture](#technical-architecture)
5. [Database Schema Design](#database-schema-design)
6. [Pydantic Models Specification](#pydantic-models-specification)
7. [API Endpoints Specification](#api-endpoints-specification)
8. [Implementation Phases](#implementation-phases)
9. [Success Criteria](#success-criteria)
10. [Testing Strategy](#testing-strategy)
11. [Dependencies and Requirements](#dependencies-and-requirements)
12. [Migration Strategy](#migration-strategy)
13. [Appendices](#appendices)

---

## Current State Analysis

### Existing Database Schema

**Current Tables:**
- `datasets`: Basic dataset information (id, title, source, landingPageUrl)
- `data_providers`: Data provider information (datacenter, name, url)
- `xml_archives`: XML archive files linked to datasets
- `useful_links`: Additional resource links for datasets

**Current Limitations:**
- Minimal metadata fields (only title, source, landing page)
- No support for distributions (different formats/access methods)
- No temporal or spatial coverage information
- No controlled vocabularies (themes, keywords)
- No support for data services
- No rights/license management
- No quality or provenance tracking
- No versioning or series relationships
- Simple provider model (not DCAT-compliant agent model)

### Technology Stack

- **Backend Framework**: FastAPI (Python 3.13)
- **ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL (with potential PostGIS extension)
- **Validation**: Pydantic 2.x
- **Migrations**: Alembic
- **Testing**: Pytest
- **Background Tasks**: Celery + Redis

---

## DCAT v3 Overview

### Core Concepts

DCAT v3 defines a standard vocabulary for describing data catalogs, datasets,
and data services on the web. It enables interoperability between catalogs and
facilitates federated search across distributed data sources.

### Class Hierarchy

```
dcat:Resource (abstract base)
├── dcat:Dataset
│   ├── dcat:DatasetSeries (new in v3)
│   └── dcat:Catalog (extends Dataset)
├── dcat:DataService
├── dcat:Distribution
└── dcat:CatalogRecord
```

### Key Principles

1. **Flexible Schema**: No strict cardinality constraints - most properties are optional and repeatable
2. **Linked Data Ready**: Uses HTTP URIs and supports RDF serialization
3. **Extensibility**: Can be extended with custom properties and profiles
4. **Namespace Reuse**: Leverages existing vocabularies (Dublin Core, FOAF, SKOS, PROV-O)
5. **Backward Compatible**: DCAT v3 is compatible with DCAT v2

### Essential Property Categories

- **Identification**: title, description, identifier
- **Classification**: theme, keyword, type
- **Temporal**: issued, modified, temporal coverage, temporal resolution
- **Spatial**: spatial coverage, bbox, centroid, spatial resolution
- **Agents**: creator, publisher, contact point
- **Rights**: license, access rights, rights statements
- **Distribution**: access URL, download URL, format, media type
- **Relationships**: qualified relations, versioning, series membership
- **Quality**: conformance, quality measurements

---

## Goals and Non-Goals

### Goals

**Primary Goals:**
- ✅ Implement complete DCAT v3-compliant database schema
- ✅ Create comprehensive Pydantic models for all DCAT entities
- ✅ Develop full CRUD API for metadata management
- ✅ Enable proper relationship modeling (many-to-many, hierarchies)
- ✅ Support spatial data with PostGIS
- ✅ Implement versioning and series relationships
- ✅ Create migration path from current schema

**Secondary Goals:**
- ✅ Maintain backward compatibility with existing data
- ✅ Design for future RDF export capability
- ✅ Optimize for query performance
- ✅ Enable faceted search capabilities

### Non-Goals

**Out of Scope for This Phase:**
- ❌ RDF serialization implementation (JSON-LD, Turtle, RDF/XML)
- ❌ Content negotiation for RDF formats
- ❌ SPARQL endpoint
- ❌ Full DQV (Data Quality Vocabulary) integration
- ❌ ODRL (Open Digital Rights Language) policy expressions
- ❌ PROV-O activity chains
- ❌ Elasticsearch schema updates (will follow in next phase)
- ❌ Frontend UI updates
- ❌ SHACL validation shapes

**These will be addressed in future iterations.**

---

## Technical Architecture

### Architecture Layers

```
┌─────────────────────────────────────────┐
│         FastAPI REST API Layer          │
│  (CRUD Endpoints, Request/Response)     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Pydantic Validation Layer          │
│  (Request/Response Models, Validators)  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│       Business Logic Layer              │
│    (CRUD Operations, Services)          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      SQLAlchemy ORM Layer               │
│     (Database Models, Queries)          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         PostgreSQL Database             │
│       (with PostGIS extension)          │
└─────────────────────────────────────────┘
```

### Design Patterns

1. **Joined Table Inheritance**: For Resource hierarchy (Resource → Dataset/DataService/Catalog)
2. **Association Tables**: For many-to-many relationships (themes, keywords, agents)
3. **Composite Models**: For structured properties (temporal coverage, spatial location)
4. **Polymorphic Relations**: For handling multiple resource types
5. **Value Objects**: For URIs, checksums, contact points

### Database Design Principles

- **Normalization**: 3NF with strategic denormalization for performance
- **Indexing**: Comprehensive indexes on foreign keys, URIs, and search fields
- **Constraints**: Foreign keys, unique constraints, check constraints
- **PostGIS Integration**: Spatial types for geographic queries
- **UUID Support**: For generating stable HTTP URIs
- **JSONB Fields**: For highly flexible metadata (controlled use)

---

## Database Schema Design

### Core Entity-Relationship Overview

```
┌──────────────┐
│   Catalog    │
│   (extends   │
│   Dataset)   │
└──────────────┘
       │
       │ contains
       ↓
┌──────────────┐      distributions      ┌──────────────┐
│   Dataset    │─────────────────────────→│Distribution  │
│              │←─────────────────────────│              │
└──────────────┘      isDistributionOf    └──────────────┘
       │                                          │
       │                                          │ accessService
       │ servesDataset                            ↓
       ↓                                   ┌──────────────┐
┌──────────────┐                          │ DataService  │
│ DataService  │                          └──────────────┘
└──────────────┘

┌──────────────┐      hasVersion         ┌──────────────┐
│   Dataset    │─────────────────────────→│   Dataset    │
│              │←─────────────────────────│   (version)  │
└──────────────┘     previousVersion      └──────────────┘

┌──────────────┐      inSeries           ┌──────────────┐
│   Dataset    │─────────────────────────→│DatasetSeries │
└──────────────┘                          └──────────────┘

┌──────────────┐      creator/publisher  ┌──────────────┐
│   Resource   │─────────────────────────→│    Agent     │
└──────────────┘                          └──────────────┘

┌──────────────┐      theme              ┌──────────────┐
│   Resource   │─────────────────────────→│    Theme     │
└──────────────┘                          │ (skos:Concept)│
                                          └──────────────┘
```

### Detailed Table Specifications

---

#### 1. Base Table: `resources`

The polymorphic base table for all DCAT resources using joined table inheritance.

```sql
CREATE TABLE resources (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL, -- 'dataset', 'data_service', 'catalog', 'dataset_series'

    -- URIs and identifiers
    uri VARCHAR(500) UNIQUE NOT NULL, -- HTTP URI for the resource
    identifier VARCHAR(255), -- External identifier (DOI, UUID, etc.)

    -- Basic descriptive metadata (Dublin Core)
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Temporal metadata
    issued TIMESTAMP WITH TIME ZONE, -- Publication date
    modified TIMESTAMP WITH TIME ZONE, -- Last modification

    -- Landing page
    landing_page VARCHAR(500), -- Human-readable entry point

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT chk_resource_type CHECK (resource_type IN ('dataset', 'data_service', 'catalog', 'dataset_series'))
);

CREATE INDEX idx_resources_type ON resources(resource_type);
CREATE INDEX idx_resources_uri ON resources(uri);
CREATE INDEX idx_resources_identifier ON resources(identifier);
CREATE INDEX idx_resources_issued ON resources(issued);
CREATE INDEX idx_resources_modified ON resources(modified);
CREATE UNIQUE INDEX idx_resources_uri_unique ON resources(uri);
```

---

#### 2. Extended Table: `datasets`

Specific properties for datasets, extends resources table.

```sql
CREATE TABLE datasets (
    -- Foreign key to base resource
    resource_id UUID PRIMARY KEY REFERENCES resources(id) ON DELETE CASCADE,

    -- Dataset-specific properties
    version VARCHAR(50), -- Version identifier
    version_notes TEXT, -- Version change description

    -- Update frequency (links to controlled vocabulary)
    accrual_periodicity_id INTEGER REFERENCES controlled_terms(id),

    -- Temporal resolution (ISO 8601 duration)
    temporal_resolution INTERVAL,

    -- Spatial resolution in meters
    spatial_resolution_in_meters NUMERIC(10, 2),

    -- Is this dataset part of a series?
    dataset_series_id UUID REFERENCES dataset_series(resource_id)
);

CREATE INDEX idx_datasets_series ON datasets(dataset_series_id);
CREATE INDEX idx_datasets_version ON datasets(version);
```

---

#### 3. Extended Table: `dataset_series`

Groups related datasets, extends datasets table.

```sql
CREATE TABLE dataset_series (
    -- Foreign key to datasets (which extends resources)
    resource_id UUID PRIMARY KEY REFERENCES datasets(resource_id) ON DELETE CASCADE,

    -- Series ordering
    first_dataset_id UUID REFERENCES datasets(resource_id), -- First in series
    last_dataset_id UUID REFERENCES datasets(resource_id)   -- Last in series
);

CREATE INDEX idx_series_first ON dataset_series(first_dataset_id);
CREATE INDEX idx_series_last ON dataset_series(last_dataset_id);
```

---

#### 4. Extended Table: `catalogs`

Catalogs of datasets and services, extends datasets.

```sql
CREATE TABLE catalogs (
    -- Foreign key to datasets (which extends resources)
    resource_id UUID PRIMARY KEY REFERENCES datasets(resource_id) ON DELETE CASCADE,

    -- Catalog-specific properties
    homepage VARCHAR(500), -- Catalog homepage

    -- Parent catalog (for hierarchical catalogs)
    parent_catalog_id UUID REFERENCES catalogs(resource_id)
);

CREATE INDEX idx_catalogs_parent ON catalogs(parent_catalog_id);
```

---

#### 5. Extended Table: `data_services`

Data services providing access to datasets, extends resources.

```sql
CREATE TABLE data_services (
    -- Foreign key to base resource
    resource_id UUID PRIMARY KEY REFERENCES resources(id) ON DELETE CASCADE,

    -- Service endpoints
    endpoint_url VARCHAR(500) NOT NULL, -- Service root URL
    endpoint_description VARCHAR(500), -- Documentation URL

    -- Service type (e.g., 'WMS', 'WFS', 'SPARQL', 'REST')
    service_type VARCHAR(100)
);

CREATE INDEX idx_services_type ON data_services(service_type);
CREATE INDEX idx_services_endpoint ON data_services(endpoint_url);
```

---

#### 6. Table: `distributions`

Different representations/access methods for datasets.

```sql
CREATE TABLE distributions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to dataset
    dataset_id UUID NOT NULL REFERENCES datasets(resource_id) ON DELETE CASCADE,

    -- Descriptive metadata
    title VARCHAR(500),
    description TEXT,

    -- Access information
    access_url VARCHAR(500) NOT NULL, -- Required: where to access
    download_url VARCHAR(500), -- Optional: direct download

    -- Format information
    media_type VARCHAR(100), -- IANA media type (e.g., 'text/csv')
    format_id INTEGER REFERENCES controlled_terms(id), -- Format from vocabulary

    -- Compression and packaging
    compress_format VARCHAR(50), -- e.g., 'gzip', 'bzip2'
    package_format VARCHAR(50), -- e.g., 'TAR', 'ZIP'

    -- Size and integrity
    byte_size BIGINT, -- Size in bytes

    -- Service providing access
    access_service_id UUID REFERENCES data_services(resource_id),

    -- License (can differ from dataset license)
    license_id INTEGER REFERENCES licenses(id),

    -- Timestamps
    issued TIMESTAMP WITH TIME ZONE,
    modified TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_distributions_dataset ON distributions(dataset_id);
CREATE INDEX idx_distributions_service ON distributions(access_service_id);
CREATE INDEX idx_distributions_media_type ON distributions(media_type);
CREATE INDEX idx_distributions_format ON distributions(format_id);
```

---

#### 7. Table: `checksums`

File integrity verification (new in DCAT v3).

```sql
CREATE TABLE checksums (
    id SERIAL PRIMARY KEY,
    distribution_id UUID NOT NULL REFERENCES distributions(id) ON DELETE CASCADE,

    -- SPDX checksum properties
    algorithm VARCHAR(50) NOT NULL, -- e.g., 'SHA256', 'MD5', 'SHA1'
    checksum_value VARCHAR(128) NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_algorithm CHECK (algorithm IN ('MD5', 'SHA1', 'SHA256', 'SHA512'))
);

CREATE INDEX idx_checksums_distribution ON checksums(distribution_id);
```

---

#### 8. Table: `agents`

Organizations and people (creators, publishers, contributors).

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,

    -- Agent identification
    uri VARCHAR(500), -- HTTP URI for the agent
    name VARCHAR(255) NOT NULL,

    -- Agent type
    agent_type VARCHAR(50) NOT NULL, -- 'organization', 'person'

    -- Contact information (can be JSONB for flexibility)
    email VARCHAR(255),
    homepage VARCHAR(500),

    -- Additional metadata (for compatibility with existing provider data)
    short_name VARCHAR(100),
    datacenter VARCHAR(255),
    biocase_url VARCHAR(500),
    is_data_center BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_agent_type CHECK (agent_type IN ('organization', 'person'))
);

CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_name ON agents(name);
CREATE UNIQUE INDEX idx_agents_uri ON agents(uri) WHERE uri IS NOT NULL;
```

---

#### 9. Table: `contact_points`

Contact information in vCard format.

```sql
CREATE TABLE contact_points (
    id SERIAL PRIMARY KEY,

    -- vCard properties
    fn VARCHAR(255), -- Full name
    organization_name VARCHAR(255),
    email VARCHAR(255),
    telephone VARCHAR(50),
    url VARCHAR(500),

    -- Address components
    street_address TEXT,
    locality VARCHAR(100), -- City
    region VARCHAR(100), -- State/Province
    postal_code VARCHAR(20),
    country_name VARCHAR(100),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contact_email ON contact_points(email);
```

---

#### 10. Association Table: `resource_agents`

Many-to-many relationship between resources and agents with roles.

```sql
CREATE TABLE resource_agents (
    id SERIAL PRIMARY KEY,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,

    -- Role specification
    role VARCHAR(50) NOT NULL, -- 'creator', 'publisher', 'contributor', 'rights_holder'

    -- Order (for multiple agents in same role)
    position INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_role CHECK (role IN ('creator', 'publisher', 'contributor', 'rights_holder', 'maintainer')),
    UNIQUE(resource_id, agent_id, role)
);

CREATE INDEX idx_resource_agents_resource ON resource_agents(resource_id);
CREATE INDEX idx_resource_agents_agent ON resource_agents(agent_id);
CREATE INDEX idx_resource_agents_role ON resource_agents(role);
```

---

#### 11. Association Table: `resource_contact_points`

Links resources to their contact points.

```sql
CREATE TABLE resource_contact_points (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    contact_point_id INTEGER NOT NULL REFERENCES contact_points(id) ON DELETE CASCADE,

    PRIMARY KEY (resource_id, contact_point_id)
);

CREATE INDEX idx_resource_contacts_resource ON resource_contact_points(resource_id);
```

---

#### 12. Table: `themes`

Controlled vocabulary for categorization (SKOS concepts).

```sql
CREATE TABLE themes (
    id SERIAL PRIMARY KEY,

    -- SKOS concept properties
    uri VARCHAR(500) UNIQUE, -- Concept URI
    pref_label VARCHAR(255) NOT NULL, -- Preferred label
    alt_label VARCHAR(255), -- Alternative label
    definition TEXT,

    -- Hierarchy
    parent_theme_id INTEGER REFERENCES themes(id),

    -- Scheme reference
    concept_scheme_id INTEGER REFERENCES concept_schemes(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_themes_uri ON themes(uri);
CREATE INDEX idx_themes_parent ON themes(parent_theme_id);
CREATE INDEX idx_themes_scheme ON themes(concept_scheme_id);
CREATE INDEX idx_themes_label ON themes(pref_label);
```

---

#### 13. Table: `concept_schemes`

Thematic taxonomies (SKOS concept schemes).

```sql
CREATE TABLE concept_schemes (
    id SERIAL PRIMARY KEY,

    uri VARCHAR(500) UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schemes_uri ON concept_schemes(uri);
```

---

#### 14. Association Table: `resource_themes`

Many-to-many between resources and themes.

```sql
CREATE TABLE resource_themes (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    theme_id INTEGER NOT NULL REFERENCES themes(id) ON DELETE CASCADE,

    PRIMARY KEY (resource_id, theme_id)
);

CREATE INDEX idx_resource_themes_resource ON resource_themes(resource_id);
CREATE INDEX idx_resource_themes_theme ON resource_themes(theme_id);
```

---

#### 15. Table: `keywords`

Free-text tags for resources.

```sql
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_keywords_keyword ON keywords(keyword);
```

---

#### 16. Association Table: `resource_keywords`

Many-to-many between resources and keywords.

```sql
CREATE TABLE resource_keywords (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,

    PRIMARY KEY (resource_id, keyword_id)
);

CREATE INDEX idx_resource_keywords_resource ON resource_keywords(resource_id);
CREATE INDEX idx_resource_keywords_keyword ON resource_keywords(keyword_id);
```

---

#### 17. Table: `temporal_coverage`

Temporal extent of resource content.

```sql
CREATE TABLE temporal_coverage (
    id SERIAL PRIMARY KEY,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    -- dcterms:PeriodOfTime properties
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,

    -- For open-ended periods
    is_ongoing BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_temporal_dates CHECK (
        start_date IS NULL OR end_date IS NULL OR start_date <= end_date
    )
);

CREATE INDEX idx_temporal_resource ON temporal_coverage(resource_id);
CREATE INDEX idx_temporal_start ON temporal_coverage(start_date);
CREATE INDEX idx_temporal_end ON temporal_coverage(end_date);
```

---

#### 18. Table: `spatial_coverage`

Geographic coverage (requires PostGIS extension).

```sql
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE spatial_coverage (
    id SERIAL PRIMARY KEY,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    -- Geographic identifiers
    location_uri VARCHAR(500), -- URI for named location
    location_name VARCHAR(255), -- Human-readable name

    -- Geometric representation (PostGIS)
    bbox GEOMETRY(POLYGON, 4326), -- Bounding box in WGS84
    centroid GEOMETRY(POINT, 4326), -- Center point in WGS84

    -- Full geometry (for complex shapes)
    geometry GEOMETRY(GEOMETRY, 4326),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_spatial_resource ON spatial_coverage(resource_id);
CREATE INDEX idx_spatial_bbox ON spatial_coverage USING GIST(bbox);
CREATE INDEX idx_spatial_centroid ON spatial_coverage USING GIST(centroid);
CREATE INDEX idx_spatial_geometry ON spatial_coverage USING GIST(geometry);
```

---

#### 19. Table: `licenses`

License information for resources and distributions.

```sql
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,

    uri VARCHAR(500) UNIQUE, -- License URI (e.g., Creative Commons)
    identifier VARCHAR(100), -- Short identifier (e.g., 'CC-BY-4.0')
    title VARCHAR(255) NOT NULL,
    description TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_licenses_uri ON licenses(uri);
CREATE INDEX idx_licenses_identifier ON licenses(identifier);
```

---

#### 20. Association Table: `resource_licenses`

Many-to-many between resources and licenses.

```sql
CREATE TABLE resource_licenses (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    license_id INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,

    PRIMARY KEY (resource_id, license_id)
);

CREATE INDEX idx_resource_licenses_resource ON resource_licenses(resource_id);
CREATE INDEX idx_resource_licenses_license ON resource_licenses(license_id);
```

---

#### 21. Table: `access_rights`

Access control and restrictions.

```sql
CREATE TABLE access_rights (
    id SERIAL PRIMARY KEY,

    uri VARCHAR(500), -- URI from controlled vocabulary
    label VARCHAR(100) NOT NULL, -- e.g., 'public', 'restricted', 'non-public'
    description TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_access_rights_label ON access_rights(label);
```

---

#### 22. Table: `resource_access_rights`

Links resources to access rights.

```sql
CREATE TABLE resource_access_rights (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    access_rights_id INTEGER NOT NULL REFERENCES access_rights(id),

    PRIMARY KEY (resource_id, access_rights_id)
);

CREATE INDEX idx_resource_access_resource ON resource_access_rights(resource_id);
```

---

#### 23. Table: `controlled_terms`

Generic controlled vocabulary terms (for types, formats, frequencies).

```sql
CREATE TABLE controlled_terms (
    id SERIAL PRIMARY KEY,

    vocabulary_name VARCHAR(100) NOT NULL, -- 'format', 'frequency', 'type'
    uri VARCHAR(500),
    code VARCHAR(100),
    label VARCHAR(255) NOT NULL,
    description TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_controlled_vocab ON controlled_terms(vocabulary_name);
CREATE INDEX idx_controlled_code ON controlled_terms(vocabulary_name, code);
```

---

#### 24. Table: `standards`

Standards and specifications (for dcterms:conformsTo).

```sql
CREATE TABLE standards (
    id SERIAL PRIMARY KEY,

    uri VARCHAR(500) UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_standards_uri ON standards(uri);
```

---

#### 25. Association Table: `resource_standards`

Resources conforming to standards.

```sql
CREATE TABLE resource_standards (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    standard_id INTEGER NOT NULL REFERENCES standards(id) ON DELETE CASCADE,

    PRIMARY KEY (resource_id, standard_id)
);

CREATE INDEX idx_resource_standards_resource ON resource_standards(resource_id);
```

---

#### 26. Table: `dataset_versions`

Version relationships between datasets.

```sql
CREATE TABLE dataset_versions (
    id SERIAL PRIMARY KEY,

    dataset_id UUID NOT NULL REFERENCES datasets(resource_id) ON DELETE CASCADE,
    related_version_id UUID NOT NULL REFERENCES datasets(resource_id) ON DELETE CASCADE,

    -- Relationship type
    relation_type VARCHAR(50) NOT NULL, -- 'has_version', 'is_version_of', 'previous_version', 'has_current_version'

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_version_relation CHECK (
        relation_type IN ('has_version', 'is_version_of', 'previous_version', 'has_current_version')
    ),
    CONSTRAINT chk_not_self_reference CHECK (dataset_id != related_version_id),
    UNIQUE(dataset_id, related_version_id, relation_type)
);

CREATE INDEX idx_versions_dataset ON dataset_versions(dataset_id);
CREATE INDEX idx_versions_related ON dataset_versions(related_version_id);
CREATE INDEX idx_versions_type ON dataset_versions(relation_type);
```

---

#### 27. Table: `dataset_series_members`

Ordered membership in dataset series.

```sql
CREATE TABLE dataset_series_members (
    id SERIAL PRIMARY KEY,

    series_id UUID NOT NULL REFERENCES dataset_series(resource_id) ON DELETE CASCADE,
    dataset_id UUID NOT NULL REFERENCES datasets(resource_id) ON DELETE CASCADE,

    -- Ordering
    position INTEGER NOT NULL,

    -- Optional prev/next explicit links
    previous_member_id UUID REFERENCES datasets(resource_id),
    next_member_id UUID REFERENCES datasets(resource_id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(series_id, dataset_id),
    UNIQUE(series_id, position)
);

CREATE INDEX idx_series_members_series ON dataset_series_members(series_id);
CREATE INDEX idx_series_members_dataset ON dataset_series_members(dataset_id);
CREATE INDEX idx_series_members_position ON dataset_series_members(series_id, position);
```

---

#### 28. Association Table: `service_datasets`

Many-to-many: services serving datasets.

```sql
CREATE TABLE service_datasets (
    service_id UUID NOT NULL REFERENCES data_services(resource_id) ON DELETE CASCADE,
    dataset_id UUID NOT NULL REFERENCES datasets(resource_id) ON DELETE CASCADE,

    PRIMARY KEY (service_id, dataset_id)
);

CREATE INDEX idx_service_datasets_service ON service_datasets(service_id);
CREATE INDEX idx_service_datasets_dataset ON service_datasets(dataset_id);
```

---

#### 29. Association Table: `catalog_resources`

Catalog membership for resources.

```sql
CREATE TABLE catalog_resources (
    catalog_id UUID NOT NULL REFERENCES catalogs(resource_id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    PRIMARY KEY (catalog_id, resource_id)
);

CREATE INDEX idx_catalog_resources_catalog ON catalog_resources(catalog_id);
CREATE INDEX idx_catalog_resources_resource ON catalog_resources(resource_id);
```

---

#### 30. Table: `catalog_records`

Metadata about catalog entries (provenance).

```sql
CREATE TABLE catalog_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links
    catalog_id UUID NOT NULL REFERENCES catalogs(resource_id) ON DELETE CASCADE,
    primary_topic_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    -- Descriptive metadata
    title VARCHAR(500),
    description TEXT,

    -- Provenance
    listing_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modification_date TIMESTAMP WITH TIME ZONE,

    -- Source information
    source_metadata_url VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(catalog_id, primary_topic_id)
);

CREATE INDEX idx_records_catalog ON catalog_records(catalog_id);
CREATE INDEX idx_records_topic ON catalog_records(primary_topic_id);
CREATE INDEX idx_records_listing_date ON catalog_records(listing_date);
```

---

#### 31. Table: `qualified_relations`

Generic relationships with roles.

```sql
CREATE TABLE qualified_relations (
    id SERIAL PRIMARY KEY,

    source_resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    target_resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    -- Relationship characterization
    relation_uri VARCHAR(500), -- URI for relation type
    relation_label VARCHAR(255),
    had_role_uri VARCHAR(500), -- Role URI
    had_role_label VARCHAR(100),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_not_self_relation CHECK (source_resource_id != target_resource_id)
);

CREATE INDEX idx_relations_source ON qualified_relations(source_resource_id);
CREATE INDEX idx_relations_target ON qualified_relations(target_resource_id);
CREATE INDEX idx_relations_role ON qualified_relations(had_role_label);
```

---

### Migration from Existing Schema

#### Mapping Table

| Current Table | Current Field | DCAT v3 Table | DCAT v3 Field | Transformation |
|---------------|---------------|---------------|---------------|----------------|
| datasets | id | datasets | resource_id | UUID conversion |
| datasets | title | resources | title | Direct copy |
| datasets | source | resources | identifier | Use as external ID |
| datasets | landingPageUrl | resources | landing_page | Direct copy |
| datasets | provider_id | resource_agents | agent_id | Create 'publisher' role |
| data_providers | id | agents | id | Direct copy |
| data_providers | name | agents | name | Direct copy |
| data_providers | datacenter | agents | datacenter | Direct copy |
| data_providers | url | agents | homepage | Direct copy |
| data_providers | biocaseUrl | agents | biocase_url | Direct copy |
| data_providers | isDataCenter | agents | is_data_center | Direct copy |
| xml_archives | * | * | * | Keep for backward compat |
| useful_links | * | * | * | Keep for backward compat |

---

## Pydantic Models Specification

### Model Organization

```
app/schemas/dcat/
├── __init__.py
├── base.py              # Base models and mixins
├── resource.py          # Resource base schema
├── dataset.py           # Dataset schemas
├── distribution.py      # Distribution schemas
├── data_service.py      # Data service schemas
├── catalog.py           # Catalog schemas
├── agent.py             # Agent and contact point schemas
├── temporal.py          # Temporal coverage schemas
├── spatial.py           # Spatial coverage schemas
├── vocabulary.py        # Themes, keywords, controlled terms
├── rights.py            # Licenses and access rights
├── relationships.py     # Versioning and qualified relations
└── validators.py        # Custom validators
```

### Base Models and Mixins

#### File: `app/schemas/dcat/base.py`

```python
"""
Base Pydantic models and mixins for DCAT entities.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, AnyUrl


class DCATBaseModel(BaseModel):
    """Base model for all DCAT schemas with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_encoders={AnyUrl: str}
    )


class IdentifiableMixin(DCATBaseModel):
    """Mixin for resources with URI and identifier."""

    uri: Optional[str] = Field(
        None,
        description="HTTP URI for the resource",
        max_length=500
    )
    identifier: Optional[str] = Field(
        None,
        description="Unique identifier (DOI, UUID, etc.)",
        max_length=255
    )


class DescriptiveMixin(DCATBaseModel):
    """Mixin for resources with title and description."""

    title: str = Field(
        ...,
        description="Name given to the resource",
        min_length=1,
        max_length=500
    )
    description: Optional[str] = Field(
        None,
        description="Free-text account of the resource"
    )


class TemporalMixin(DCATBaseModel):
    """Mixin for resources with temporal metadata."""

    issued: Optional[datetime] = Field(
        None,
        description="Date of formal issuance/publication"
    )
    modified: Optional[datetime] = Field(
        None,
        description="Most recent date on which the resource was changed"
    )


class TimestampMixin(DCATBaseModel):
    """Mixin for database timestamps."""

    created_at: Optional[datetime] = Field(
        None,
        description="Record creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Record last update timestamp"
    )


class URIReference(DCATBaseModel):
    """Reference to a resource by URI."""

    uri: str = Field(..., description="Resource URI")
    label: Optional[str] = Field(None, description="Human-readable label")
```

---

### Resource Models

#### File: `app/schemas/dcat/resource.py`

```python
"""
Base Resource schemas for DCAT.
"""
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import Field, field_validator

from .base import (
    DCATBaseModel,
    IdentifiableMixin,
    DescriptiveMixin,
    TemporalMixin,
    TimestampMixin
)


class ResourceBase(
    IdentifiableMixin,
    DescriptiveMixin,
    TemporalMixin,
    TimestampMixin
):
    """
    Base schema for all catalogued resources.
    Maps to dcat:Resource class.
    """

    id: Optional[UUID] = Field(None, description="Internal resource ID")
    resource_type: Literal['dataset', 'data_service', 'catalog', 'dataset_series']
    landing_page: Optional[str] = Field(
        None,
        description="Web page that can be navigated to",
        max_length=500
    )

    @field_validator('landing_page')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('landing_page must be a valid HTTP(S) URL')
        return v


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""

    # Exclude auto-generated fields
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResourceUpdate(DCATBaseModel):
    """Schema for updating a resource (all fields optional)."""

    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    identifier: Optional[str] = Field(None, max_length=255)
    landing_page: Optional[str] = Field(None, max_length=500)
    issued: Optional[datetime] = None
    modified: Optional[datetime] = None


class ResourceResponse(ResourceBase):
    """Schema for resource API responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime
```

---

### Agent Models

#### File: `app/schemas/dcat/agent.py`

```python
"""
Agent and ContactPoint schemas for DCAT.
Maps to foaf:Agent and vcard:Kind.
"""
from typing import Optional, Literal
from pydantic import Field, EmailStr

from .base import DCATBaseModel, TimestampMixin


class ContactPointBase(DCATBaseModel):
    """
    Contact point in vCard format.
    Maps to vcard:Kind.
    """

    fn: Optional[str] = Field(None, description="Full name", max_length=255)
    organization_name: Optional[str] = Field(
        None,
        description="Organization name",
        max_length=255
    )
    email: Optional[EmailStr] = Field(None, description="Email address")
    telephone: Optional[str] = Field(None, description="Telephone number", max_length=50)
    url: Optional[str] = Field(None, description="Contact URL", max_length=500)

    # Address
    street_address: Optional[str] = None
    locality: Optional[str] = Field(None, description="City", max_length=100)
    region: Optional[str] = Field(None, description="State/Province", max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_name: Optional[str] = Field(None, max_length=100)


class ContactPointCreate(ContactPointBase):
    """Schema for creating a contact point."""
    pass


class ContactPointResponse(ContactPointBase, TimestampMixin):
    """Schema for contact point responses."""

    id: int


class AgentBase(DCATBaseModel):
    """
    Agent (organization or person).
    Maps to foaf:Agent.
    """

    uri: Optional[str] = Field(None, description="Agent URI", max_length=500)
    name: str = Field(..., description="Agent name", max_length=255)
    agent_type: Literal['organization', 'person'] = Field(
        ...,
        description="Type of agent"
    )

    # Contact information
    email: Optional[EmailStr] = None
    homepage: Optional[str] = Field(None, max_length=500)

    # Legacy provider fields (for backward compatibility)
    short_name: Optional[str] = Field(None, max_length=100)
    datacenter: Optional[str] = Field(None, max_length=255)
    biocase_url: Optional[str] = Field(None, max_length=500)
    is_data_center: bool = False


class AgentCreate(AgentBase):
    """Schema for creating an agent."""
    pass


class AgentUpdate(DCATBaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    homepage: Optional[str] = Field(None, max_length=500)
    short_name: Optional[str] = Field(None, max_length=100)
    datacenter: Optional[str] = Field(None, max_length=255)
    biocase_url: Optional[str] = Field(None, max_length=500)
    is_data_center: Optional[bool] = None


class AgentResponse(AgentBase, TimestampMixin):
    """Schema for agent responses."""

    id: int


class ResourceAgentAssociation(DCATBaseModel):
    """Association between resource and agent with role."""

    agent_id: int
    role: Literal['creator', 'publisher', 'contributor', 'rights_holder', 'maintainer']
    position: int = 0


class ResourceAgentResponse(DCATBaseModel):
    """Response schema for resource-agent relationship."""

    agent: AgentResponse
    role: str
    position: int
```

---

### Dataset Models

#### File: `app/schemas/dcat/dataset.py`

```python
"""
Dataset schemas for DCAT.
Maps to dcat:Dataset.
"""
from typing import Optional, List
from uuid import UUID
from datetime import timedelta
from decimal import Decimal
from pydantic import Field, field_validator

from .base import DCATBaseModel
from .resource import ResourceBase, ResourceCreate, ResourceUpdate, ResourceResponse
from .agent import ResourceAgentResponse, ContactPointResponse
from .distribution import DistributionResponse
from .temporal import TemporalCoverageResponse
from .spatial import SpatialCoverageResponse
from .vocabulary import ThemeResponse, KeywordResponse
from .rights import LicenseResponse, AccessRightsResponse


class DatasetBase(ResourceBase):
    """
    Base schema for datasets.
    Maps to dcat:Dataset.
    """

    resource_type: Literal['dataset'] = 'dataset'

    # Version information
    version: Optional[str] = Field(None, description="Version indicator", max_length=50)
    version_notes: Optional[str] = Field(
        None,
        description="Description of version differences"
    )

    # Accrual periodicity (from controlled vocabulary)
    accrual_periodicity_code: Optional[str] = Field(
        None,
        description="Frequency of updates (e.g., 'annual', 'monthly')"
    )

    # Resolutions
    temporal_resolution: Optional[timedelta] = Field(
        None,
        description="Minimum time period between observations"
    )
    spatial_resolution_in_meters: Optional[Decimal] = Field(
        None,
        description="Minimum spatial separation in meters",
        decimal_places=2
    )

    # Series membership
    dataset_series_id: Optional[UUID] = Field(
        None,
        description="Parent dataset series ID"
    )


class DatasetCreate(DatasetBase):
    """Schema for creating a dataset."""

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Related entities (IDs only)
    theme_ids: List[int] = Field(default_factory=list)
    keyword_ids: List[int] = Field(default_factory=list)
    agent_associations: List[ResourceAgentAssociation] = Field(default_factory=list)
    contact_point_ids: List[int] = Field(default_factory=list)
    license_ids: List[int] = Field(default_factory=list)
    access_rights_ids: List[int] = Field(default_factory=list)
    standard_ids: List[int] = Field(default_factory=list)


class DatasetUpdate(ResourceUpdate):
    """Schema for updating a dataset."""

    version: Optional[str] = Field(None, max_length=50)
    version_notes: Optional[str] = None
    accrual_periodicity_code: Optional[str] = None
    temporal_resolution: Optional[timedelta] = None
    spatial_resolution_in_meters: Optional[Decimal] = None
    dataset_series_id: Optional[UUID] = None

    # Related entities updates
    theme_ids: Optional[List[int]] = None
    keyword_ids: Optional[List[int]] = None
    agent_associations: Optional[List[ResourceAgentAssociation]] = None
    contact_point_ids: Optional[List[int]] = None
    license_ids: Optional[List[int]] = None
    access_rights_ids: Optional[List[int]] = None


class DatasetResponse(DatasetBase):
    """Schema for dataset responses with full related entities."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    # Related entities (full objects)
    themes: List[ThemeResponse] = Field(default_factory=list)
    keywords: List[KeywordResponse] = Field(default_factory=list)
    agents: List[ResourceAgentResponse] = Field(default_factory=list)
    contact_points: List[ContactPointResponse] = Field(default_factory=list)
    distributions: List[DistributionResponse] = Field(default_factory=list)
    temporal_coverage: List[TemporalCoverageResponse] = Field(default_factory=list)
    spatial_coverage: List[SpatialCoverageResponse] = Field(default_factory=list)
    licenses: List[LicenseResponse] = Field(default_factory=list)
    access_rights: List[AccessRightsResponse] = Field(default_factory=list)


class DatasetListResponse(DCATBaseModel):
    """Schema for paginated dataset list."""

    total: int
    page: int
    page_size: int
    datasets: List[DatasetResponse]
```

---

### Distribution Models

#### File: `app/schemas/dcat/distribution.py`

```python
"""
Distribution schemas for DCAT.
Maps to dcat:Distribution.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import Field, field_validator

from .base import DCATBaseModel, TimestampMixin, DescriptiveMixin, TemporalMixin


class ChecksumBase(DCATBaseModel):
    """
    Checksum for integrity verification.
    Maps to spdx:Checksum (new in DCAT v3).
    """

    algorithm: Literal['MD5', 'SHA1', 'SHA256', 'SHA512'] = Field(
        ...,
        description="Hash algorithm"
    )
    checksum_value: str = Field(
        ...,
        description="Hexadecimal hash value",
        max_length=128
    )


class ChecksumCreate(ChecksumBase):
    """Schema for creating a checksum."""
    pass


class ChecksumResponse(ChecksumBase, TimestampMixin):
    """Schema for checksum responses."""

    id: int
    distribution_id: UUID


class DistributionBase(DescriptiveMixin, TemporalMixin):
    """
    Base schema for distributions.
    Maps to dcat:Distribution.
    """

    # Required access information
    access_url: str = Field(
        ...,
        description="URL providing access to the distribution",
        max_length=500
    )

    # Optional direct download
    download_url: Optional[str] = Field(
        None,
        description="Direct download URL",
        max_length=500
    )

    # Format information
    media_type: Optional[str] = Field(
        None,
        description="IANA media type",
        max_length=100
    )
    format_id: Optional[int] = Field(
        None,
        description="Format from controlled vocabulary"
    )

    # Compression and packaging
    compress_format: Optional[str] = Field(
        None,
        description="Compression format (e.g., 'gzip')",
        max_length=50
    )
    package_format: Optional[str] = Field(
        None,
        description="Package format (e.g., 'TAR', 'ZIP')",
        max_length=50
    )

    # Size
    byte_size: Optional[int] = Field(
        None,
        description="Size in bytes",
        ge=0
    )

    # Related entities
    access_service_id: Optional[UUID] = Field(
        None,
        description="Data service providing access"
    )
    license_id: Optional[int] = Field(
        None,
        description="License (if different from dataset)"
    )

    @field_validator('access_url', 'download_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://', 'ftp://')):
            raise ValueError('Must be a valid URL')
        return v


class DistributionCreate(DistributionBase):
    """Schema for creating a distribution."""

    dataset_id: UUID = Field(..., description="Parent dataset ID")
    checksums: List[ChecksumCreate] = Field(default_factory=list)


class DistributionUpdate(DCATBaseModel):
    """Schema for updating a distribution."""

    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    access_url: Optional[str] = Field(None, max_length=500)
    download_url: Optional[str] = Field(None, max_length=500)
    media_type: Optional[str] = Field(None, max_length=100)
    format_id: Optional[int] = None
    compress_format: Optional[str] = Field(None, max_length=50)
    package_format: Optional[str] = Field(None, max_length=50)
    byte_size: Optional[int] = Field(None, ge=0)
    access_service_id: Optional[UUID] = None
    license_id: Optional[int] = None


class DistributionResponse(DistributionBase, TimestampMixin):
    """Schema for distribution responses."""

    id: UUID
    dataset_id: UUID
    created_at: datetime
    updated_at: datetime

    checksums: List[ChecksumResponse] = Field(default_factory=list)
```

---

### Data Service Models

#### File: `app/schemas/dcat/data_service.py`

```python
"""
Data Service schemas for DCAT.
Maps to dcat:DataService.
"""
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import Field, field_validator

from .base import DCATBaseModel
from .resource import ResourceBase, ResourceCreate, ResourceUpdate, ResourceResponse
from .agent import ResourceAgentResponse


class DataServiceBase(ResourceBase):
    """
    Base schema for data services.
    Maps to dcat:DataService.
    """

    resource_type: Literal['data_service'] = 'data_service'

    # Service endpoints
    endpoint_url: str = Field(
        ...,
        description="Root location or primary endpoint URL",
        max_length=500
    )
    endpoint_description: Optional[str] = Field(
        None,
        description="URL of documentation describing the service",
        max_length=500
    )

    # Service type
    service_type: Optional[str] = Field(
        None,
        description="Type of service (e.g., 'WMS', 'WFS', 'REST')",
        max_length=100
    )

    @field_validator('endpoint_url', 'endpoint_description')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Must be a valid HTTP(S) URL')
        return v


class DataServiceCreate(DataServiceBase):
    """Schema for creating a data service."""

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Datasets served by this service
    dataset_ids: List[UUID] = Field(
        default_factory=list,
        description="Datasets served by this service"
    )

    # Agent associations
    agent_associations: List[ResourceAgentAssociation] = Field(default_factory=list)


class DataServiceUpdate(ResourceUpdate):
    """Schema for updating a data service."""

    endpoint_url: Optional[str] = Field(None, max_length=500)
    endpoint_description: Optional[str] = Field(None, max_length=500)
    service_type: Optional[str] = Field(None, max_length=100)

    dataset_ids: Optional[List[UUID]] = None
    agent_associations: Optional[List[ResourceAgentAssociation]] = None


class DataServiceResponse(DataServiceBase):
    """Schema for data service responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    agents: List[ResourceAgentResponse] = Field(default_factory=list)
    served_dataset_ids: List[UUID] = Field(default_factory=list)
```

---

### Temporal Coverage Models

#### File: `app/schemas/dcat/temporal.py`

```python
"""
Temporal coverage schemas for DCAT.
Maps to dcterms:PeriodOfTime.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import Field, field_validator

from .base import DCATBaseModel, TimestampMixin


class TemporalCoverageBase(DCATBaseModel):
    """
    Temporal coverage period.
    Maps to dcterms:PeriodOfTime.
    """

    start_date: Optional[datetime] = Field(
        None,
        description="Start of the period"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End of the period"
    )
    is_ongoing: bool = Field(
        default=False,
        description="Whether this is an open-ended period"
    )

    @field_validator('end_date')
    @classmethod
    def validate_end_after_start(cls, v, info):
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class TemporalCoverageCreate(TemporalCoverageBase):
    """Schema for creating temporal coverage."""

    resource_id: UUID


class TemporalCoverageUpdate(DCATBaseModel):
    """Schema for updating temporal coverage."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_ongoing: Optional[bool] = None


class TemporalCoverageResponse(TemporalCoverageBase, TimestampMixin):
    """Schema for temporal coverage responses."""

    id: int
    resource_id: UUID
```

---

### Spatial Coverage Models

#### File: `app/schemas/dcat/spatial.py`

```python
"""
Spatial coverage schemas for DCAT.
Maps to dcterms:Location with PostGIS geometries.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator

from .base import DCATBaseModel, TimestampMixin


class SpatialCoverageBase(DCATBaseModel):
    """
    Spatial coverage with geographic information.
    Maps to dcterms:Location.
    """

    # Named location
    location_uri: Optional[str] = Field(
        None,
        description="URI for a named location",
        max_length=500
    )
    location_name: Optional[str] = Field(
        None,
        description="Human-readable location name",
        max_length=255
    )

    # Geometric representations (GeoJSON format for API)
    bbox: Optional[Dict[str, Any]] = Field(
        None,
        description="Bounding box as GeoJSON"
    )
    centroid: Optional[Dict[str, Any]] = Field(
        None,
        description="Center point as GeoJSON"
    )
    geometry: Optional[Dict[str, Any]] = Field(
        None,
        description="Full geometry as GeoJSON"
    )

    @field_validator('bbox', 'centroid', 'geometry')
    @classmethod
    def validate_geojson(cls, v: Optional[Dict]) -> Optional[Dict]:
        if v:
            if 'type' not in v or 'coordinates' not in v:
                raise ValueError('Invalid GeoJSON format')
        return v


class SpatialCoverageCreate(SpatialCoverageBase):
    """Schema for creating spatial coverage."""

    resource_id: UUID


class SpatialCoverageUpdate(DCATBaseModel):
    """Schema for updating spatial coverage."""

    location_uri: Optional[str] = Field(None, max_length=500)
    location_name: Optional[str] = Field(None, max_length=255)
    bbox: Optional[Dict[str, Any]] = None
    centroid: Optional[Dict[str, Any]] = None
    geometry: Optional[Dict[str, Any]] = None


class SpatialCoverageResponse(SpatialCoverageBase, TimestampMixin):
    """Schema for spatial coverage responses."""

    id: int
    resource_id: UUID
```

---

### Vocabulary Models

#### File: `app/schemas/dcat/vocabulary.py`

```python
"""
Vocabulary schemas for DCAT (themes, keywords, controlled terms).
Maps to SKOS concepts and schemes.
"""
from typing import Optional, List
from pydantic import Field

from .base import DCATBaseModel, TimestampMixin


class ConceptSchemeBase(DCATBaseModel):
    """
    Thematic taxonomy.
    Maps to skos:ConceptScheme.
    """

    uri: Optional[str] = Field(None, max_length=500)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None


class ConceptSchemeCreate(ConceptSchemeBase):
    """Schema for creating a concept scheme."""
    pass


class ConceptSchemeResponse(ConceptSchemeBase, TimestampMixin):
    """Schema for concept scheme responses."""

    id: int


class ThemeBase(DCATBaseModel):
    """
    Theme or category.
    Maps to skos:Concept.
    """

    uri: Optional[str] = Field(None, description="Concept URI", max_length=500)
    pref_label: str = Field(
        ...,
        description="Preferred label",
        max_length=255
    )
    alt_label: Optional[str] = Field(
        None,
        description="Alternative label",
        max_length=255
    )
    definition: Optional[str] = Field(None, description="Concept definition")

    # Hierarchy
    parent_theme_id: Optional[int] = Field(None, description="Parent theme")
    concept_scheme_id: Optional[int] = Field(None, description="Concept scheme")


class ThemeCreate(ThemeBase):
    """Schema for creating a theme."""
    pass


class ThemeUpdate(DCATBaseModel):
    """Schema for updating a theme."""

    pref_label: Optional[str] = Field(None, max_length=255)
    alt_label: Optional[str] = Field(None, max_length=255)
    definition: Optional[str] = None
    parent_theme_id: Optional[int] = None
    concept_scheme_id: Optional[int] = None


class ThemeResponse(ThemeBase, TimestampMixin):
    """Schema for theme responses."""

    id: int


class KeywordBase(DCATBaseModel):
    """Free-text keyword."""

    keyword: str = Field(..., description="Keyword text", max_length=100)


class KeywordCreate(KeywordBase):
    """Schema for creating a keyword."""
    pass


class KeywordResponse(KeywordBase, TimestampMixin):
    """Schema for keyword responses."""

    id: int


class ControlledTermBase(DCATBaseModel):
    """
    Generic controlled vocabulary term.
    For formats, frequencies, types, etc.
    """

    vocabulary_name: str = Field(
        ...,
        description="Vocabulary name (e.g., 'format', 'frequency')",
        max_length=100
    )
    uri: Optional[str] = Field(None, max_length=500)
    code: Optional[str] = Field(None, max_length=100)
    label: str = Field(..., max_length=255)
    description: Optional[str] = None


class ControlledTermCreate(ControlledTermBase):
    """Schema for creating a controlled term."""
    pass


class ControlledTermResponse(ControlledTermBase, TimestampMixin):
    """Schema for controlled term responses."""

    id: int
```

---

### Rights Models

#### File: `app/schemas/dcat/rights.py`

```python
"""
Rights and licensing schemas for DCAT.
Maps to dcterms:LicenseDocument and dcterms:RightsStatement.
"""
from typing import Optional
from pydantic import Field

from .base import DCATBaseModel, TimestampMixin


class LicenseBase(DCATBaseModel):
    """
    License document.
    Maps to dcterms:LicenseDocument.
    """

    uri: Optional[str] = Field(
        None,
        description="License URI (e.g., Creative Commons)",
        max_length=500
    )
    identifier: Optional[str] = Field(
        None,
        description="Short identifier (e.g., 'CC-BY-4.0')",
        max_length=100
    )
    title: str = Field(..., description="License title", max_length=255)
    description: Optional[str] = Field(None, description="License description")


class LicenseCreate(LicenseBase):
    """Schema for creating a license."""
    pass


class LicenseUpdate(DCATBaseModel):
    """Schema for updating a license."""

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class LicenseResponse(LicenseBase, TimestampMixin):
    """Schema for license responses."""

    id: int


class AccessRightsBase(DCATBaseModel):
    """
    Access rights statement.
    Maps to dcterms:RightsStatement.
    """

    uri: Optional[str] = Field(None, max_length=500)
    label: str = Field(
        ...,
        description="Rights label (e.g., 'public', 'restricted')",
        max_length=100
    )
    description: Optional[str] = None


class AccessRightsCreate(AccessRightsBase):
    """Schema for creating access rights."""
    pass


class AccessRightsResponse(AccessRightsBase, TimestampMixin):
    """Schema for access rights responses."""

    id: int


class StandardBase(DCATBaseModel):
    """
    Standard or specification.
    For dcterms:conformsTo.
    """

    uri: Optional[str] = Field(None, max_length=500)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)


class StandardCreate(StandardBase):
    """Schema for creating a standard."""
    pass


class StandardResponse(StandardBase, TimestampMixin):
    """Schema for standard responses."""

    id: int
```

---

## API Endpoints Specification

### Base URL Structure

All DCAT endpoints will be under `/api/v1/dcat/` to maintain clean separation from legacy endpoints.

### Endpoint Organization

```
/api/v1/dcat/
├── /datasets              # Dataset CRUD
├── /distributions         # Distribution CRUD
├── /data-services         # Data service CRUD
├── /catalogs              # Catalog CRUD
├── /agents                # Agent CRUD
├── /contact-points        # Contact point CRUD
├── /themes                # Theme vocabulary CRUD
├── /keywords              # Keyword CRUD
├── /licenses              # License CRUD
├── /access-rights         # Access rights CRUD
├── /standards             # Standards CRUD
├── /controlled-terms      # Controlled vocabulary CRUD
└── /spatial-search        # Spatial query endpoints
```

---

### Dataset Endpoints

#### File: `app/api/v1/endpoints/dcat/datasets.py`

```python
"""
Dataset CRUD endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.dcat.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetListResponse
)
from app.crud.dcat import dataset as crud_dataset


router = APIRouter()


@router.post(
    "/",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dataset"
)
async def create_dataset(
    *,
    db: Session = Depends(get_db),
    dataset_in: DatasetCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new dataset with metadata.

    - **title**: Dataset title (required)
    - **description**: Dataset description
    - **themes**: List of theme IDs for categorization
    - **keywords**: List of keyword IDs for tagging
    - **distributions**: List of distributions (access methods)
    - **agents**: Creator, publisher associations
    """
    dataset = crud_dataset.create(db=db, obj_in=dataset_in)
    return dataset


@router.get(
    "/",
    response_model=DatasetListResponse,
    summary="List datasets with pagination"
)
async def list_datasets(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    theme_id: Optional[int] = Query(None, description="Filter by theme ID"),
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    agent_id: Optional[int] = Query(None, description="Filter by agent (creator/publisher)"),
    issued_after: Optional[datetime] = Query(None, description="Filter by issue date"),
    search: Optional[str] = Query(None, description="Full-text search in title/description")
):
    """
    Retrieve a paginated list of datasets.

    Supports filtering by:
    - Theme
    - Keyword
    - Agent (creator/publisher)
    - Issue date
    - Full-text search
    """
    datasets, total = crud_dataset.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        theme_id=theme_id,
        keyword=keyword,
        agent_id=agent_id,
        issued_after=issued_after,
        search=search
    )

    return DatasetListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        datasets=datasets
    )


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset by ID"
)
async def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific dataset by ID.

    Returns full dataset metadata including:
    - Basic metadata (title, description, dates)
    - Themes and keywords
    - Distributions (access methods)
    - Agents (creators, publishers)
    - Spatial and temporal coverage
    - Licenses and rights
    """
    dataset = crud_dataset.get(db=db, id=dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    return dataset


@router.put(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Update dataset"
)
async def update_dataset(
    *,
    db: Session = Depends(get_db),
    dataset_id: UUID,
    dataset_in: DatasetUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update an existing dataset.

    All fields are optional - only provided fields will be updated.
    """
    dataset = crud_dataset.get(db=db, id=dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )

    dataset = crud_dataset.update(db=db, db_obj=dataset, obj_in=dataset_in)
    return dataset


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dataset"
)
async def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a dataset and all its related entities (cascading delete).
    """
    dataset = crud_dataset.get(db=db, id=dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )

    crud_dataset.remove(db=db, id=dataset_id)
    return None


# Additional specific endpoints

@router.get(
    "/{dataset_id}/distributions",
    response_model=List[DistributionResponse],
    summary="Get dataset distributions"
)
async def get_dataset_distributions(
    dataset_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all distributions for a dataset."""
    from app.crud.dcat import distribution as crud_distribution

    distributions = crud_distribution.get_by_dataset(db=db, dataset_id=dataset_id)
    return distributions


@router.get(
    "/{dataset_id}/versions",
    response_model=List[DatasetResponse],
    summary="Get dataset versions"
)
async def get_dataset_versions(
    dataset_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all versions of a dataset."""
    versions = crud_dataset.get_versions(db=db, dataset_id=dataset_id)
    return versions


@router.post(
    "/{dataset_id}/themes/{theme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add theme to dataset"
)
async def add_theme_to_dataset(
    dataset_id: UUID,
    theme_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Associate a theme with a dataset."""
    crud_dataset.add_theme(db=db, dataset_id=dataset_id, theme_id=theme_id)
    return None


@router.delete(
    "/{dataset_id}/themes/{theme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove theme from dataset"
)
async def remove_theme_from_dataset(
    dataset_id: UUID,
    theme_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove theme association from dataset."""
    crud_dataset.remove_theme(db=db, dataset_id=dataset_id, theme_id=theme_id)
    return None
```

---

### Distribution Endpoints

#### File: `app/api/v1/endpoints/dcat/distributions.py`

```python
"""
Distribution CRUD endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.dcat.distribution import (
    DistributionCreate,
    DistributionUpdate,
    DistributionResponse
)
from app.crud.dcat import distribution as crud_distribution


router = APIRouter()


@router.post(
    "/",
    response_model=DistributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new distribution"
)
async def create_distribution(
    *,
    db: Session = Depends(get_db),
    distribution_in: DistributionCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new distribution for a dataset.

    A distribution represents a specific way to access dataset data:
    - Different formats (CSV, JSON, XML)
    - Different protocols (HTTP download, API, FTP)
    - Different subsets or aggregations
    """
    distribution = crud_distribution.create(db=db, obj_in=distribution_in)
    return distribution


@router.get(
    "/{distribution_id}",
    response_model=DistributionResponse,
    summary="Get distribution by ID"
)
async def get_distribution(
    distribution_id: UUID,
    db: Session = Depends(get_db)
):
    """Retrieve a specific distribution by ID."""
    distribution = crud_distribution.get(db=db, id=distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution {distribution_id} not found"
        )
    return distribution


@router.put(
    "/{distribution_id}",
    response_model=DistributionResponse,
    summary="Update distribution"
)
async def update_distribution(
    *,
    db: Session = Depends(get_db),
    distribution_id: UUID,
    distribution_in: DistributionUpdate,
    current_user = Depends(get_current_user)
):
    """Update an existing distribution."""
    distribution = crud_distribution.get(db=db, id=distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution {distribution_id} not found"
        )

    distribution = crud_distribution.update(
        db=db,
        db_obj=distribution,
        obj_in=distribution_in
    )
    return distribution


@router.delete(
    "/{distribution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete distribution"
)
async def delete_distribution(
    distribution_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a distribution."""
    distribution = crud_distribution.get(db=db, id=distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution {distribution_id} not found"
        )

    crud_distribution.remove(db=db, id=distribution_id)
    return None
```

---

### Agent Endpoints

#### File: `app/api/v1/endpoints/dcat/agents.py`

```python
"""
Agent (organization/person) CRUD endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.dcat.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse
)
from app.crud.dcat import agent as crud_agent


router = APIRouter()


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent"
)
async def create_agent(
    *,
    db: Session = Depends(get_db),
    agent_in: AgentCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new agent (organization or person).

    Agents can be:
    - Organizations (data centers, institutions)
    - Persons (individual researchers)

    Agents can have multiple roles:
    - Creator: produced the dataset
    - Publisher: makes the dataset available
    - Contributor: contributed to the dataset
    - Rights holder: holds rights to the dataset
    """
    agent = crud_agent.create(db=db, obj_in=agent_in)
    return agent


@router.get(
    "/",
    response_model=List[AgentResponse],
    summary="List agents"
)
async def list_agents(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    search: Optional[str] = Query(None, description="Search by name")
):
    """List agents with pagination and filtering."""
    agents = crud_agent.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        agent_type=agent_type,
        search=search
    )
    return agents


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID"
)
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific agent by ID."""
    agent = crud_agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent"
)
async def update_agent(
    *,
    db: Session = Depends(get_db),
    agent_id: int,
    agent_in: AgentUpdate,
    current_user = Depends(get_current_user)
):
    """Update an existing agent."""
    agent = crud_agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    agent = crud_agent.update(db=db, db_obj=agent, obj_in=agent_in)
    return agent


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent"
)
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete an agent."""
    agent = crud_agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    crud_agent.remove(db=db, id=agent_id)
    return None
```

---

### Similar endpoints should be created for:
- Data Services (`data_services.py`)
- Catalogs (`catalogs.py`)
- Themes (`themes.py`)
- Keywords (`keywords.py`)
- Licenses (`licenses.py`)
- Contact Points (`contact_points.py`)
- Access Rights (`access_rights.py`)
- Standards (`standards.py`)
- Temporal Coverage (`temporal_coverage.py`)
- Spatial Coverage (`spatial_coverage.py`)

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Set up core infrastructure and base models.

**Tasks**:
1. Database setup
   - Enable PostGIS extension
   - Create base `resources` table
   - Set up Alembic migration structure
2. Base Pydantic models
   - Base classes and mixins
   - Resource base schema
3. Initial CRUD operations
   - Basic resource CRUD utilities
4. Testing framework
   - pytest configuration
   - Database fixtures
   - Test utilities

**Deliverables**:
- Database migration for base tables
- Base Pydantic models
- Testing infrastructure
- Documentation setup

---

### Phase 2: Core Entities (Weeks 3-4)

**Goal**: Implement main DCAT entities.

**Tasks**:
1. Database tables
   - Datasets table
   - Distributions table
   - Agents table
   - Association tables (resource_agents, etc.)
2. Pydantic models
   - Dataset schemas
   - Distribution schemas
   - Agent schemas
3. CRUD operations
   - Dataset CRUD
   - Distribution CRUD
   - Agent CRUD
4. API endpoints
   - Dataset endpoints
   - Distribution endpoints
   - Agent endpoints

**Deliverables**:
- Core database schema
- Complete CRUD operations
- RESTful API endpoints
- Unit tests

---

### Phase 3: Metadata Extensions (Weeks 5-6)

**Goal**: Add rich metadata capabilities.

**Tasks**:
1. Database tables
   - Temporal coverage
   - Spatial coverage
   - Themes and keywords
   - Licenses and rights
2. Pydantic models
   - Temporal/spatial schemas
   - Vocabulary schemas
   - Rights schemas
3. CRUD operations
   - Temporal/spatial CRUD
   - Vocabulary management
   - Rights management
4. API endpoints
   - Metadata endpoints
   - Vocabulary endpoints

**Deliverables**:
- Extended metadata schema
- Vocabulary management
- Spatial query support
- Integration tests

---

### Phase 4: Advanced Features (Weeks 7-8)

**Goal**: Implement versioning, relationships, and data services.

**Tasks**:
1. Database tables
   - Dataset versions
   - Dataset series
   - Data services
   - Catalogs
   - Qualified relations
2. Pydantic models
   - Versioning schemas
   - Service schemas
   - Catalog schemas
3. CRUD operations
   - Version management
   - Service management
   - Catalog management
4. API endpoints
   - Versioning endpoints
   - Service endpoints
   - Catalog endpoints

**Deliverables**:
- Complete DCAT v3 schema
- Advanced relationship support
- Full API coverage
- End-to-end tests

---

### Phase 5: Migration and Optimization (Weeks 9-10)

**Goal**: Migrate existing data and optimize performance.

**Tasks**:
1. Data migration
   - Migration scripts
   - Data transformation
   - Validation
2. Performance optimization
   - Query optimization
   - Index tuning
   - Caching strategy
3. Documentation
   - API documentation (OpenAPI)
   - Database schema docs
   - Migration guide
   - Developer guide
4. Testing
   - Performance tests
   - Load tests
   - Compliance validation

**Deliverables**:
- Migrated data
- Optimized queries
- Complete documentation
- Production-ready system

---

## Success Criteria

### Functional Requirements

✅ **Database Layer**
- All DCAT v3 core classes implemented
- All required properties stored
- Proper relationship modeling
- PostGIS integration working
- Migration from old schema successful

✅ **Validation Layer**
- Complete Pydantic models
- Field validation working
- Type checking passing
- Custom validators implemented

✅ **API Layer**
- All CRUD endpoints implemented
- Proper HTTP status codes
- Error handling
- Authentication/authorization
- API documentation (OpenAPI/Swagger)

### Non-Functional Requirements

✅ **Performance**
- List queries < 200ms for 1000 records
- Single resource retrieval < 50ms
- Bulk operations support
- Proper indexing

✅ **Data Quality**
- No data loss from migration
- Referential integrity maintained
- Consistent data state

✅ **Code Quality**
- > 80% test coverage
- Type hints throughout
- Linting passing (ruff/black)
- Documentation complete

✅ **Standards Compliance**
- DCAT v3 property mapping complete
- URI patterns correct
- Relationship semantics correct
- Ready for RDF export (future)

---

## Testing Strategy

### Test Levels

#### 1. Unit Tests

**Target**: Individual functions and methods
**Coverage**: > 80%

**Test categories**:
- Pydantic model validation
- Field validators
- CRUD operations
- Utility functions

**Example**:
```python
def test_dataset_title_required():
    """Test that dataset title is required."""
    with pytest.raises(ValidationError):
        DatasetCreate(description="Test")

def test_dataset_creation():
    """Test dataset creation with valid data."""
    dataset = DatasetCreate(
        title="Test Dataset",
        resource_type="dataset"
    )
    assert dataset.title == "Test Dataset"
```

#### 2. Integration Tests

**Target**: Database operations and API endpoints
**Coverage**: All CRUD operations

**Test categories**:
- Database queries
- Relationship handling
- Transaction management
- API endpoint responses

**Example**:
```python
def test_create_dataset_with_themes(db_session):
    """Test creating dataset with themes."""
    theme = crud_theme.create(db_session, ThemeCreate(pref_label="Biology"))
    dataset = crud_dataset.create(
        db_session,
        DatasetCreate(
            title="Test",
            resource_type="dataset",
            theme_ids=[theme.id]
        )
    )
    assert len(dataset.themes) == 1
    assert dataset.themes[0].pref_label == "Biology"
```

#### 3. API Tests

**Target**: HTTP endpoints
**Coverage**: All endpoints

**Test categories**:
- Request/response validation
- Status codes
- Authentication
- Error handling

**Example**:
```python
def test_create_dataset_api(client, auth_headers):
    """Test dataset creation via API."""
    response = client.post(
        "/api/v1/dcat/datasets/",
        json={"title": "Test", "resource_type": "dataset"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

#### 4. Performance Tests

**Target**: Query performance
**Coverage**: Critical paths

**Test categories**:
- Query execution time
- N+1 query detection
- Bulk operation performance

**Example**:
```python
def test_dataset_list_performance(db_session, benchmark):
    """Test dataset listing performance."""
    # Create 1000 datasets
    for i in range(1000):
        crud_dataset.create(
            db_session,
            DatasetCreate(title=f"Dataset {i}", resource_type="dataset")
        )

    # Benchmark query
    result = benchmark(crud_dataset.get_multi, db_session, limit=100)
    assert len(result[0]) == 100
```

#### 5. Migration Tests

**Target**: Data migration integrity
**Coverage**: All migration paths

**Test categories**:
- Data preservation
- Relationship integrity
- Foreign key constraints

---

## Dependencies and Requirements

### Python Packages

**Core**:
```
fastapi>=0.110.0
sqlalchemy>=2.0.25
alembic>=1.13.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
psycopg2-binary>=2.9.9
```

**Database Extensions**:
```
geoalchemy2>=0.14.3  # PostGIS integration
```

**Development**:
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-postgresql>=5.0.0
black>=24.0.0
ruff>=0.1.0
mypy>=1.8.0
```

**Optional (Future Phases)**:
```
rdflib>=7.0.0  # RDF serialization
pyshacl>=0.25.0  # DCAT validation
```

### Database Requirements

**PostgreSQL**: >= 14
**Extensions**:
- `postgis` (spatial support)
- `uuid-ossp` (UUID generation)

### Infrastructure

- Redis (for Celery, existing)
- Docker containers (existing setup)
- Traefik (existing reverse proxy)

---

## Migration Strategy

### Migration Approach

**Strategy**: Parallel systems with gradual transition

**Phases**:

1. **Phase 1: Parallel Implementation**
   - New DCAT schema alongside existing schema
   - No changes to existing tables
   - New API endpoints under `/api/v1/dcat/`

2. **Phase 2: Data Synchronization**
   - Sync existing data to new schema
   - Validation of migration
   - Keep both systems in sync

3. **Phase 3: API Migration**
   - Update frontend to use new endpoints
   - Maintain backward compatibility
   - Gradual deprecation of old endpoints

4. **Phase 4: Cleanup**
   - Remove old schema (optional)
   - Archive legacy endpoints
   - Full transition complete

### Backward Compatibility

**Maintained**:
- Existing `datasets` and `data_providers` tables kept
- Legacy API endpoints functional
- XML archives and useful links preserved

**Mapping Layer**:
- Views mapping old schema to new
- API adapters for legacy endpoints
- Documentation of mappings

### Migration Scripts

Location: `backend/app/migrations/dcat_migration/`

**Scripts**:
1. `001_migrate_providers_to_agents.py` - Convert providers to agents
2. `002_migrate_datasets_to_resources.py` - Convert datasets to DCAT datasets
3. `003_create_distributions.py` - Create distributions from XML archives
4. `004_validate_migration.py` - Verify data integrity

---

## Appendices

### Appendix A: URI Pattern Conventions

**Pattern**: `https://aggregator.gfbio.org/{resource-type}/{uuid}`

**Examples**:
- Dataset: `https://aggregator.gfbio.org/dataset/550e8400-e29b-41d4-a716-446655440000`
- Distribution: `https://aggregator.gfbio.org/distribution/550e8400-e29b-41d4-a716-446655440001`
- Data Service: `https://aggregator.gfbio.org/service/550e8400-e29b-41d4-a716-446655440002`

### Appendix B: Controlled Vocabularies

**Initial Vocabularies to Load**:

1. **Dublin Core Frequency** (accrual periodicity)
   - annual, monthly, weekly, daily, irregular, continuous

2. **Access Rights**
   - public, restricted, non-public

3. **Media Types** (from IANA)
   - text/csv, application/json, application/xml, etc.

4. **GFBio Themes** (domain-specific)
   - taxonomy, ecology, biodiversity, genomics, etc.

### Appendix C: DCAT v3 to Database Mapping

Complete mapping table showing how every DCAT property maps to database columns.

| DCAT Property | DCAT Class | DB Table | DB Column | Notes |
|---------------|------------|----------|-----------|-------|
| dcterms:title | Resource | resources | title | Required |
| dcterms:description | Resource | resources | description | |
| dcterms:identifier | Resource | resources | identifier | |
| dcat:landingPage | Resource | resources | landing_page | |
| dcterms:issued | Resource | resources | issued | |
| dcterms:modified | Resource | resources | modified | |
| dcat:distribution | Dataset | distributions | dataset_id (FK) | 1:N |
| dcat:theme | Resource | resource_themes | theme_id (FK) | M:N |
| dcat:keyword | Resource | resource_keywords | keyword_id (FK) | M:N |
| dcterms:creator | Resource | resource_agents | agent_id + role='creator' | M:N |
| dcterms:publisher | Resource | resource_agents | agent_id + role='publisher' | M:N |
| dcat:contactPoint | Resource | resource_contact_points | contact_point_id (FK) | M:N |
| dcterms:temporal | Resource | temporal_coverage | start_date, end_date | 1:N |
| dcterms:spatial | Resource | spatial_coverage | bbox, centroid | 1:N |
| dcterms:license | Resource | resource_licenses | license_id (FK) | M:N |
| dcterms:accessRights | Resource | resource_access_rights | access_rights_id (FK) | M:N |
| dcat:version | Dataset | datasets | version | |
| dcat:previousVersion | Dataset | dataset_versions | relation_type='previous_version' | M:N |
| dcat:inSeries | Dataset | dataset_series_members | series_id (FK) | M:N |
| dcat:spatialResolutionInMeters | Dataset | datasets | spatial_resolution_in_meters | |
| dcat:temporalResolution | Dataset | datasets | temporal_resolution | |
| dcat:endpointURL | DataService | data_services | endpoint_url | Required for services |
| dcat:servesDataset | DataService | service_datasets | dataset_id (FK) | M:N |
| dcat:accessURL | Distribution | distributions | access_url | Required |
| dcat:downloadURL | Distribution | distributions | download_url | |
| dcat:mediaType | Distribution | distributions | media_type | |
| dcat:byteSize | Distribution | distributions | byte_size | |
| spdx:checksum | Distribution | checksums | algorithm, checksum_value | 1:N |

### Appendix D: PostGIS Geometry Handling

**GeoJSON to PostGIS Conversion**:

```python
from geoalchemy2 import Geometry, WKTElement
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
import json

def geojson_to_postgis(geojson_dict):
    """Convert GeoJSON dict to PostGIS geometry."""
    geom = shape(geojson_dict)
    return from_shape(geom, srid=4326)

def postgis_to_geojson(postgis_geom):
    """Convert PostGIS geometry to GeoJSON dict."""
    from geoalchemy2.shape import to_shape
    geom = to_shape(postgis_geom)
    return geom.__geo_interface__
```

**Spatial Query Examples**:

```python
from sqlalchemy import func
from geoalchemy2 import Geometry

# Find datasets intersecting a bounding box
bbox_wkt = 'POLYGON((min_lon min_lat, ...)'
results = db.query(DatasetModel).join(SpatialCoverageModel).filter(
    func.ST_Intersects(
        SpatialCoverageModel.bbox,
        func.ST_GeomFromText(bbox_wkt, 4326)
    )
).all()

# Find datasets within distance of a point
point_wkt = 'POINT(lon lat)'
distance_meters = 10000
results = db.query(DatasetModel).join(SpatialCoverageModel).filter(
    func.ST_DWithin(
        func.ST_Transform(SpatialCoverageModel.centroid, 3857),
        func.ST_Transform(func.ST_GeomFromText(point_wkt, 4326), 3857),
        distance_meters
    )
).all()
```

### Appendix E: Example API Requests

**Create Dataset**:
```bash
curl -X POST "http://aggregator.gfbio.org/api/v1/dcat/datasets/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Marine Biodiversity Dataset",
    "description": "Comprehensive marine species observations",
    "resource_type": "dataset",
    "theme_ids": [1, 5],
    "keyword_ids": [10, 15, 23],
    "agent_associations": [
      {"agent_id": 3, "role": "creator", "position": 0},
      {"agent_id": 7, "role": "publisher", "position": 0}
    ]
  }'
```

**Create Distribution**:
```bash
curl -X POST "http://aggregator.gfbio.org/api/v1/dcat/distributions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "CSV Download",
    "access_url": "https://data.gfbio.org/datasets/marine/download",
    "download_url": "https://data.gfbio.org/datasets/marine/data.csv",
    "media_type": "text/csv",
    "byte_size": 1048576,
    "checksums": [
      {"algorithm": "SHA256", "checksum_value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
    ]
  }'
```

**Search Datasets**:
```bash
curl "http://aggregator.gfbio.org/api/v1/dcat/datasets/?theme_id=5&search=marine&limit=20"
```

---

## Glossary

**DCAT**: Data Catalog Vocabulary - W3C standard for describing datasets and data services

**RDF**: Resource Description Framework - framework for representing information on the web

**SKOS**: Simple Knowledge Organization System - standard for representing controlled vocabularies

**Dublin Core**: Metadata standard providing core properties (title, creator, date, etc.)

**PostGIS**: PostgreSQL extension for geographic/spatial data

**vCard**: Standard for contact information

**SPDX**: Software Package Data Exchange - standard including checksum definitions

**FOAF**: Friend of a Friend - vocabulary for describing people and organizations

**PROV-O**: Provenance Ontology - for representing provenance information

**DQV**: Data Quality Vocabulary - for describing data quality

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-15 | Technical Team | Initial draft |

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Tech Lead | | | |
| Database Architect | | | |

---

**END OF DOCUMENT**
