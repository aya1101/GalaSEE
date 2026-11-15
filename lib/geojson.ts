import type { FeatureCollection, Geometry } from "geojson";

export type RegionProperties = {
  id: string;
  kind: "study" | "mangrove" | "anomaly";
  title: string;
  location?: string;
  areaHa?: number;
  confidence?: number;
  description?: string;
  radarDb?: string;
  tideM?: string;
  browseUrl?: string;
  browseCompositeUrl?: string;
  browseHHHHUrl?: string;
  browseHVHVUrl?: string;
  nativeKmlUrl?: string;
  sceneName?: string;
  startTime?: string;
  stopTime?: string;
  processingLevel?: string;
  collectionId?: string;
  fileName?: string;
};

export const studyAreaGeoJson: FeatureCollection<Geometry, { id: string; kind: "study"; title: string }> = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "STUDY-AREA",
      properties: { id: "STUDY-AREA", kind: "study", title: "Khu vực nghiên cứu" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [106.8027, 10.5878], [106.7603, 10.5401], [106.7762, 10.4901], [106.7951, 10.4193],
          [106.83, 10.3991], [106.858, 10.376], [106.8989, 10.3686], [106.9444, 10.3835],
          [106.9785, 10.4051], [106.9858, 10.4495], [107.0018, 10.4783], [107.003, 10.5007],
          [107.0095, 10.5185], [107.0215, 10.5299], [107.0276, 10.5443], [107.0121, 10.5532],
          [107.0061, 10.5672], [107.0207, 10.5731], [107.0233, 10.5917], [107.0095, 10.6116],
          [106.9987, 10.6188], [107.0005, 10.6364], [107.0151, 10.6351], [107.0207, 10.6638],
          [107.0155, 10.6807], [106.9905, 10.676], [106.9828, 10.6599], [106.9708, 10.6502],
          [106.951, 10.6434], [106.9389, 10.6481], [106.9312, 10.657], [106.9105, 10.6591],
          [106.9101, 10.6401], [106.8985, 10.6303], [106.8826, 10.6494], [106.8718, 10.6434],
          [106.846, 10.6392], [106.8027, 10.5878],
        ]],
      },
    },
  ],
};

export const demoGeoJson: FeatureCollection<Geometry, RegionProperties> = {
  type: "FeatureCollection",
  features: [
    { type: "Feature", id: "STUDY-001", properties: { id: "STUDY-001", kind: "study", title: "Cửa Dinh – Cồn Ba Lá" }, geometry: { type: "Polygon", coordinates: [[[106.72, 10.30], [106.79, 10.51], [106.94, 10.50], [106.99, 10.38], [106.93, 10.25], [106.78, 10.22], [106.72, 10.30]]] } },
    { type: "Feature", id: "MNG-047", properties: { id: "MNG-047", kind: "mangrove", title: "Khu vực #MNG-047", location: "Cửa Dinh – Cồn Ba Lá", areaHa: 412.6, confidence: .93, description: "Phát hiện thay đổi cấu trúc thảm thực vật so với chu kỳ trước. Cần kiểm tra thực địa.", radarDb: "−12,4", tideM: "1,24" }, geometry: { type: "Polygon", coordinates: [[[106.80, 10.38], [106.82, 10.43], [106.87, 10.44], [106.89, 10.39], [106.86, 10.34], [106.81, 10.34], [106.80, 10.38]]] } },
    { type: "Feature", id: "MNG-021", properties: { id: "MNG-021", kind: "mangrove", title: "Khu vực #MNG-021", location: "Cửa Dinh", areaHa: 268.4, confidence: .89, description: "Thảm thực vật ổn định trong ba chu kỳ quan sát gần nhất.", radarDb: "−10,8", tideM: "1,18" }, geometry: { type: "Polygon", coordinates: [[[106.75, 10.39], [106.77, 10.44], [106.82, 10.45], [106.83, 10.40], [106.79, 10.35], [106.74, 10.35], [106.75, 10.39]]] } },
    { type: "Feature", id: "MNG-063", properties: { id: "MNG-063", kind: "mangrove", title: "Khu vực #MNG-063", location: "Cồn Ba Lá", areaHa: 325.1, confidence: .91, description: "Mật độ tán rừng cao, chưa ghi nhận tín hiệu đáng chú ý.", radarDb: "−11,9", tideM: "1,31" }, geometry: { type: "Polygon", coordinates: [[[106.82, 10.28], [106.85, 10.34], [106.91, 10.36], [106.94, 10.31], [106.91, 10.25], [106.85, 10.24], [106.82, 10.28]]] } },
    { type: "Feature", id: "MNG-088", properties: { id: "MNG-088", kind: "mangrove", title: "Khu vực #MNG-088", location: "Vàm Rạch", areaHa: 184.3, confidence: .86, description: "Vùng rừng ven cửa sông đang được theo dõi định kỳ.", radarDb: "−13,1", tideM: "1,09" }, geometry: { type: "Polygon", coordinates: [[[106.87, 10.44], [106.92, 10.45], [106.96, 10.40], [106.94, 10.35], [106.89, 10.37], [106.87, 10.44]]] } },
    { type: "Feature", id: "AN-012", properties: { id: "AN-012", kind: "anomaly", title: "Bất thường #AN-012", location: "Phía đông Cửa Dinh", areaHa: 14.8, confidence: .84, description: "Tín hiệu giảm phản xạ radar cục bộ, có thể liên quan đến thay đổi mặt nước hoặc tán rừng.", radarDb: "−18,6", tideM: "1,27" }, geometry: { type: "Polygon", coordinates: [[[106.90, 10.40], [106.92, 10.41], [106.95, 10.40], [106.94, 10.38], [106.91, 10.38], [106.90, 10.40]]] } },
    { type: "Feature", id: "AN-019", properties: { id: "AN-019", kind: "anomaly", title: "Bất thường #AN-019", location: "Bờ nam khu nghiên cứu", areaHa: 8.6, confidence: .78, description: "Biên rừng dịch chuyển so với ảnh quan sát tháng trước.", radarDb: "−17,2", tideM: "1,11" }, geometry: { type: "Polygon", coordinates: [[[106.84, 10.29], [106.86, 10.30], [106.87, 10.28], [106.85, 10.27], [106.84, 10.29]]] } },
    { type: "Feature", id: "AN-031", properties: { id: "AN-031", kind: "anomaly", title: "Bất thường #AN-031", location: "Cồn Ba Lá", areaHa: 21.2, confidence: .81, description: "Phát hiện vùng có biến động cấu trúc tán rừng rõ hơn nền khu vực.", radarDb: "−16,4", tideM: "1,35" }, geometry: { type: "Polygon", coordinates: [[[106.77, 10.36], [106.79, 10.37], [106.80, 10.35], [106.78, 10.34], [106.77, 10.36]]] } },
  ],
};
