param([string]$InitialDirectory = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class JanviFolderPicker {
    [ComImport, Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    private class FileOpenDialog { }
    [ComImport, Guid("42F85136-DB7E-439C-85F1-E4075D135FC8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IFileDialog {
        [PreserveSig] int Show(IntPtr owner);
        void SetFileTypes(uint count, IntPtr filters);
        void SetFileTypeIndex(uint index);
        void GetFileTypeIndex(out uint index);
        void Advise(IntPtr events, out uint cookie);
        void Unadvise(uint cookie);
        void SetOptions(uint options);
        void GetOptions(out uint options);
        void SetDefaultFolder(IShellItem item);
        void SetFolder(IShellItem item);
        void GetFolder(out IShellItem item);
        void GetCurrentSelection(out IShellItem item);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string name);
        void GetFileName(out IntPtr name);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string title);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void GetResult(out IShellItem item);
    }
    [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellItem {
        void BindToHandler(IntPtr bind, ref Guid handler, ref Guid iid, out IntPtr result);
        void GetParent(out IShellItem parent);
        void GetDisplayName(uint type, out IntPtr name);
        void GetAttributes(uint mask, out uint attributes);
        void Compare(IShellItem other, uint hint, out int order);
    }
    [DllImport("shell32.dll", CharSet=CharSet.Unicode, PreserveSig=false)]
    private static extern void SHCreateItemFromParsingName(string path, IntPtr context, ref Guid iid, out IShellItem item);
    public static string Choose(string initial) {
        IFileDialog dialog = (IFileDialog)new FileOpenDialog();
        try {
            uint options; dialog.GetOptions(out options);
            dialog.SetOptions(options | 0x20 | 0x40 | 0x800);
            dialog.SetTitle("Select folder");
            if (!String.IsNullOrEmpty(initial) && System.IO.Directory.Exists(initial)) {
                IShellItem folder = null;
                try { Guid iid = typeof(IShellItem).GUID; SHCreateItemFromParsingName(initial, IntPtr.Zero, ref iid, out folder); dialog.SetFolder(folder); }
                finally { if (folder != null) Marshal.ReleaseComObject(folder); }
            }
            int hr = dialog.Show(IntPtr.Zero);
            if (hr == unchecked((int)0x800704C7)) return "";
            if (hr != 0) Marshal.ThrowExceptionForHR(hr);
            IShellItem selected; dialog.GetResult(out selected);
            try {
                IntPtr name; selected.GetDisplayName(0x80058000, out name);
                try { return Marshal.PtrToStringUni(name); }
                finally { Marshal.FreeCoTaskMem(name); }
            } finally { Marshal.ReleaseComObject(selected); }
        } finally { Marshal.ReleaseComObject(dialog); }
    }
}
'@
$selected = [JanviFolderPicker]::Choose($InitialDirectory)
@{ selected_path = $selected } | ConvertTo-Json -Compress
