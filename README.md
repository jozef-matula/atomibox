Atomibox Backup Service
===========

Distributed backup (mirroring) system for large volumes of data inspired in a sense by "Git content management".

This tool shall allow mirroring of files from selected directories onto a remote computer over a secure connection. As a "backup" tool, this service identifies deleted or modified files and even file renames (here comes the Git "content tracking" inspiration) and keeps separately copies of original files for later restoration. This tool has been developed to provide remote-site backup of a photo archive as well as other personal files and documents - this means it is designed to cope well with hundred of thousands files with sizes in tens of MB. 

Atomibox has ambition to work across different platforms (e.g. having Windows home coputer with remote backup on a cheap Linux server), therefore by-design it does not care too much about file metadata such a permissions or ownership. What it takes care about if file content (referer as "atoms"), making sure that no file content gets lost. For example after accidental removal of a file, remote mirror preserves the file (content) in backup location.
