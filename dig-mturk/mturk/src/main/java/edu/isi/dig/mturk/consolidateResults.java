package edu.isi.dig.mturk;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;

import com.amazonaws.AmazonClientException;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ListObjectsRequest;
import com.amazonaws.services.s3.model.ObjectListing;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectSummary;

public class consolidateResults {
	String resultFile = "", fileContent = "";
	private String bucketName = "", prefixKey = "", targetFolder = "";
	private AmazonS3 s3client;

	public consolidateResults(String bucketName) {
		this.bucketName = "aisoftwareresearch/ner/" + bucketName + "/hits";
		this.targetFolder = "aisoftwareresearch/ner/" + bucketName;
		this.prefixKey = "ner/" + bucketName + "/hits";
		s3client = hitFiles.ConnectToAWS();
	}
	public void getAllResults() {
		String mainBucket = "aisoftwareresearch", result = "",content="";
		try {
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				result ="HitId\t WorkerId\tAssignmentId\tSentenceId\tOffset\tHightlighted Text\tCategory\tText\tEncoded Text\n"; 
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							if (keyParts.length == 1) {
								resultFile = keyParts[0] + "/" + keyParts[0] + ".tsv";
								S3Object in_object = s3client.getObject(new GetObjectRequest(
										bucketName, resultFile));
								InputStream in_objectData = in_object.getObjectContent();
								BufferedReader in_reader = new BufferedReader(
										new InputStreamReader(in_objectData));
								//discard first line as it will be heading
								content = in_reader.readLine();
								while ((content = in_reader.readLine()) != null) {
									result += content + "\n";
								}
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());
			uploadFile("consolidatedResult", "tsv",result);
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}
	public void uploadFile(String filename, String fileType, String fileContent) {
		String keyName = filename + "." + fileType;
		try {
			InputStream inputStream = new ByteArrayInputStream(
					fileContent.getBytes());
			ObjectMetadata metadata = new ObjectMetadata();
			/*
			 * Set content length. Else stream contents will be buffered in
			 * memory and could result in out of memory errors.
			 */
			metadata.setContentLength(fileContent.length());
			PutObjectRequest request = new PutObjectRequest(targetFolder,
					keyName, inputStream, metadata);
			s3client.putObject(request);
		} catch (AmazonServiceException ase) {
			System.out.println("Error Message:    " + ase.getMessage());
		} catch (AmazonClientException ace) {
			System.out.println("Error Message: " + ace.getMessage());
		}
		
	}
	public static void main(String args[]) {
		if (args[0] == null) {
			System.out.println();
		} else {
			consolidateResults results = new consolidateResults(args[0]);
			results.getAllResults();
		}
	}
}
