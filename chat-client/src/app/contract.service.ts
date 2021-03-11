import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract, Method } from './contract';
import { Page } from './statement';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private url = "http://localhost:5001/ibc/contract";

  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient) { }

  getUrl() {
    return this.url;
  }

  getStatements(name: string, method: Method): Observable<Page> {
    const url = `${this.url}/${name}`;
    return this.http.put<Page>(url, method, this.httpOptions).pipe(
      tap((page: Page) => console.log(page)),
      catchError(this.handleError<Page>(`getContract name=${name}`))
    );
  }

  createStatement(name: string, method: Method): Observable<any> {
    const url = `${this.url}/${name}`;
    console.log(url);
    console.log(method);
    console.log(this.httpOptions);
    return this.http.put<any>(url, method, this.httpOptions).pipe(
      tap(_ => console.log('created statement')),
      catchError(this.handleError<any>(`createStatement name=${name}`))
    );
  }

  getContracts(): Observable<Contract[]> {
    return this.http.get<Contract[]>(this.url).pipe(
        tap(_ => console.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }

}
