import React, { useState } from "react";
import { UploadCloud, CheckCircle2, AlertCircle, FileText, ArrowRight, Copy } from "lucide-react";
import { useUploadCVs, useBatchProgress } from "../../api/uploads";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";

interface UploadPageProps {
  requisitionId: number;
  onUploadDone?: () => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ requisitionId, onUploadDone }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState("");

  const uploadMutation = useUploadCVs(requisitionId);
  const { data: progress } = useBatchProgress(activeBatchId);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles(filesArray);
      setUploadError("");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const filesArray = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.endsWith(".pdf") || f.name.endsWith(".docx")
      );
      setSelectedFiles(filesArray);
      setUploadError("");
    }
  };

  const handleStartUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploadError("");
    try {
      const res = await uploadMutation.mutateAsync(selectedFiles);
      setActiveBatchId(res.batch_id);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload files");
    }
  };

  const isBatchFinished =
    progress && progress.total > 0 && progress.done + progress.failed >= progress.total;

  return (
    <div className="space-y-6">
      {/* Upload Dropzone */}
      <Card className="p-8 bg-white border-dashed border-2 border-gray-300 hover:border-blue-400 transition-colors">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          className="flex flex-col items-center justify-center text-center cursor-pointer"
        >
          <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-3">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Drag and drop resumes here, or browse
          </h3>
          <p className="text-xs text-gray-500 mb-4 max-w-sm">
            Upload up to 500 files per batch in PDF or DOCX format (max 5 MB per file).
          </p>
          <label className="cursor-pointer">
            <input
              type="file"
              multiple
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              className="hidden"
            />
            <span className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-colors shadow-xs">
              Select Files
            </span>
          </label>
        </div>

        {selectedFiles.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between">
            <div className="text-xs text-gray-600 font-medium">
              {selectedFiles.length} file{selectedFiles.length === 1 ? "" : "s"} selected
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedFiles([])}
                disabled={uploadMutation.isPending}
              >
                Clear
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartUpload}
                isLoading={uploadMutation.isPending}
              >
                Upload & Start Screening
              </Button>
            </div>
          </div>
        )}
      </Card>

      {uploadError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md flex items-start gap-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Batch Processing Progress */}
      {progress && (
        <Card className="p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-gray-900">
                Batch #{progress.batch_id} Processing Progress
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {progress.done} processed, {progress.queued + progress.running} remaining, {progress.failed} failed
              </p>
            </div>

            {isBatchFinished && onUploadDone && (
              <Button
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-4 h-4 ml-1" />}
                onClick={onUploadDone}
              >
                View Ranked Candidates
              </Button>
            )}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-blue-600 h-2.5 transition-all duration-300 ease-out"
              style={{
                width: `${progress.total > 0 ? ((progress.done + progress.failed) / progress.total) * 100 : 0}%`,
              }}
            />
          </div>

          {/* Per-File Progress Table */}
          <div className="border border-gray-200 rounded-md overflow-hidden mt-4">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50 text-gray-600 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-2 text-left">File Name</th>
                  <th className="px-4 py-2 text-left">Candidate</th>
                  <th className="px-4 py-2 text-left">Size</th>
                  <th className="px-4 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {progress.files.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 flex items-center gap-1.5 font-medium text-gray-900">
                      <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                      <span className="truncate max-w-xs">{file.filename}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">
                      {file.candidate_name || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">
                      {(file.size / 1024).toFixed(0)} KB
                    </td>
                    <td className="px-4 py-2.5">
                      {file.parse_status === "ok" && (
                        <Badge variant="success" size="sm">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Parsed</span>
                        </Badge>
                      )}
                      {file.parse_status === "needs_review" && (
                        <Badge variant="warning" size="sm">
                          {file.is_duplicate ? (
                            <Copy className="w-3 h-3 text-amber-600" />
                          ) : (
                            <AlertCircle className="w-3 h-3 text-amber-600" />
                          )}
                          <span>{file.is_duplicate ? "Duplicate" : "Needs Review"}</span>
                        </Badge>
                      )}
                      {file.parse_status === "failed" && (
                        <Badge variant="danger" size="sm" title={file.parse_error || ""}>
                          <AlertCircle className="w-3 h-3 text-red-600" />
                          <span>Failed: {file.parse_error || "Error"}</span>
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
