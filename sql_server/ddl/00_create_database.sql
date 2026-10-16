/* =====================================================================
   RxSource - synthetic NHS England primary-care prescribing (OLTP source)
   00: create the database.
   Run with:  sqlcmd -S localhost -E -C -b -i sql_server\ddl\00_create_database.sql
   WARNING: drops RxSource if it already exists.
   ===================================================================== */
USE master;
GO

IF DB_ID(N'RxSource') IS NOT NULL
BEGIN
    ALTER DATABASE RxSource SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE RxSource;
END
GO

CREATE DATABASE RxSource;
GO

-- SIMPLE recovery: this is a rebuildable dev source, and it lets bcp bulk loads be minimally logged.
ALTER DATABASE RxSource SET RECOVERY SIMPLE;
GO

USE RxSource;
GO

CREATE SCHEMA rx AUTHORIZATION dbo;
GO
